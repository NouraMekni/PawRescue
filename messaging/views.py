from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from animals.models import Animal
from reports.models import Report
from shelters.models import Refuge

from .models import Conversation, Message, UserBlock
from .serializers import (
    ConversationCreateSerializer,
    ConversationSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)
from .services import (
    counterparty_of_participant,
    find_conversation,
    is_blocked,
    is_party,
    other_user,
    party_user_ids,
    push_to_users,
)


def visible_conversations(user):
    return Conversation.objects.select_related(
        "refuge",
        "refuge__user",
        "veterinaire",
        "participant",
        "requested_by",
    ).filter(Q(participant=user) | Q(veterinaire=user) | Q(refuge__user=user))


def get_visible_conversation(user, pk):
    return get_object_or_404(visible_conversations(user), pk=pk)


class RefugeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = (
            User.objects.filter(role=User.Role.REFUGE)
            .select_related("refuge")
            .order_by("first_name", "last_name", "email")
        )
        return Response([_refuge_card(_refuge_for_user(user), request) for user in users])


class VeterinaireListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        vets = (
            User.objects.filter(role=User.Role.VETERINAIRE)
            .select_related("veterinaire_profile")
            .order_by("first_name", "last_name", "email")
        )
        return Response([_vet_card(vet, request) for vet in vets])


class ConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ConversationSerializer(many=True)})
    def get(self, request):
        conversations = visible_conversations(request.user)
        return Response(
            ConversationSerializer(conversations, many=True, context={"request": request}).data
        )

    @extend_schema(request=ConversationCreateSerializer, responses={201: ConversationSerializer})
    def post(self, request):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        refuge, veterinaire, participant, error = _parties(request.user, data)
        if error is not None:
            return error

        report = _linked_report(data.get("report"), refuge, participant)
        if isinstance(report, Response):
            return report
        animal = _linked_animal(data.get("animal"), refuge)
        if isinstance(animal, Response):
            return animal

        counterpart = refuge.user if refuge is not None else veterinaire
        if is_blocked(request.user, counterpart):
            return Response(
                {"detail": "Vous ne pouvez pas envoyer de message."},
                status=status.HTTP_403_FORBIDDEN,
            )

        existing = find_conversation(participant, report, refuge=refuge, veterinaire=veterinaire)
        if existing is not None:
            if existing.status == Conversation.Status.BLOCKED or is_blocked(
                existing.participant, counterparty_of_participant(existing)
            ):
                return Response(
                    {"detail": "Vous ne pouvez pas envoyer de message."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response(ConversationSerializer(existing, context={"request": request}).data)

        conversation = Conversation.objects.create(
            refuge=refuge,
            veterinaire=veterinaire,
            participant=participant,
            report=report,
            animal=animal,
            status=Conversation.Status.PENDING,
            requested_by=request.user,
        )
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            body=data["body"],
        )
        _notify(
            conversation,
            {
                "type": "message.created",
                "conversation_id": conversation.id,
                "message": MessageSerializer(message).data,
            },
        )
        _notify_message(conversation, message)
        return Response(
            ConversationSerializer(conversation, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        conversation = get_visible_conversation(request.user, pk)
        conversation.messages.exclude(sender=request.user).update(is_read=True)
        return Response(ConversationSerializer(conversation, context={"request": request}).data)


class MessageCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        conversation = get_visible_conversation(request.user, pk)
        if not is_party(request.user, conversation):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if conversation.status == Conversation.Status.BLOCKED or is_blocked(
            conversation.participant, counterparty_of_participant(conversation)
        ):
            return Response(
                {"detail": "Vous ne pouvez pas envoyer de message."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if conversation.status != Conversation.Status.ACCEPTED:
            return Response(
                {"detail": "En attente d'acceptation."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            body=serializer.validated_data["body"],
        )
        conversation.save(update_fields=["updated_at"])
        payload = {
            "type": "message.created",
            "conversation_id": conversation.id,
            "message": MessageSerializer(message).data,
        }
        _notify(conversation, payload)
        _notify_message(conversation, message)
        return Response(payload["message"], status=status.HTTP_201_CREATED)


class ConversationAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        conversation = get_visible_conversation(request.user, pk)
        if conversation.status != Conversation.Status.PENDING:
            return Response(
                {"detail": "Cette demande n'est plus en attente."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if conversation.requested_by_id == request.user.id:
            return Response(
                {"detail": "Seul le destinataire peut accepter la demande."},
                status=status.HTTP_403_FORBIDDEN,
            )
        conversation.status = Conversation.Status.ACCEPTED
        conversation.save(update_fields=["status", "updated_at"])
        _notify(
            conversation,
            {"type": "conversation.accepted", "conversation_id": conversation.id},
        )
        _notify_user(
            conversation.requested_by or other_user(request.user, conversation),
            type="request_accepted",
            title="Demande acceptée",
            body="Vous pouvez maintenant échanger des messages.",
            conversation=conversation,
        )
        return Response(ConversationSerializer(conversation, context={"request": request}).data)


class ConversationBlockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        conversation = get_visible_conversation(request.user, pk)
        if conversation.requested_by_id == request.user.id and conversation.status == Conversation.Status.PENDING:
            return Response(
                {"detail": "Seul le destinataire peut bloquer cette demande."},
                status=status.HTTP_403_FORBIDDEN,
            )
        blocked = other_user(request.user, conversation)
        UserBlock.objects.get_or_create(blocker=request.user, blocked=blocked)
        conversation.status = Conversation.Status.BLOCKED
        conversation.blocked_by = request.user
        conversation.save(update_fields=["status", "blocked_by", "updated_at"])
        _notify(
            conversation,
            {"type": "conversation.blocked", "conversation_id": conversation.id},
        )
        _notify_user(
            blocked,
            type="conversation_blocked",
            title="Conversation bloquée",
            body="Vous ne pouvez pas envoyer de message.",
            conversation=conversation,
        )
        return Response(ConversationSerializer(conversation, context={"request": request}).data)


def _parties(user, data):
    refuge = data.get("refuge")
    veterinaire = data.get("veterinaire")
    if user.role == User.Role.REFUGE and refuge is None and veterinaire is None:
        own_refuge = getattr(user, "refuge", None)
        participant = data.get("participant")
        if own_refuge is None:
            return None, None, None, Response(
                {"detail": "Complétez le profil du refuge avant d'écrire."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if participant is None or participant.id == user.id:
            return None, None, None, Response(
                {"participant": "Choisissez la personne à contacter."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return own_refuge, None, participant, None

    if refuge is not None and veterinaire is not None:
        return None, None, None, Response(
            {"detail": "Choisissez un refuge ou un vétérinaire."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if refuge is not None:
        return refuge, None, user, None
    if veterinaire is not None:
        if veterinaire.id == user.id:
            return None, None, None, Response(
                {"detail": "Vous ne pouvez pas vous écrire à vous-même."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None, veterinaire, user, None
    return None, None, None, Response(
        {"detail": "Choisissez un refuge ou un vétérinaire."},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _linked_report(report_id, refuge, participant):
    if not report_id:
        return None
    report = Report.objects.filter(pk=report_id).first()
    if report is None:
        return Response({"report": "Signalement introuvable."}, status=status.HTTP_400_BAD_REQUEST)
    assigned_here = refuge is not None and report.assigned_refuge_id == refuge.id
    if report.reporter_id != participant.id and not assigned_here:
        return Response(
            {"report": "Ce signalement n'appartient pas à cette conversation."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return report


def _linked_animal(animal_id, refuge):
    if not animal_id:
        return None
    if refuge is None:
        return Response(
            {"animal": "Un animal se rattache à un refuge."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    animal = Animal.objects.filter(pk=animal_id, refuge=refuge).first()
    if animal is None:
        return Response({"animal": "Animal introuvable pour ce refuge."}, status=status.HTTP_400_BAD_REQUEST)
    return animal


def _notify(conversation, payload):
    push_to_users(party_user_ids(conversation), payload)


def _notify_message(conversation, message):
    recipient_ids = party_user_ids(conversation) - {message.sender_id}
    recipients = User.objects.filter(id__in=recipient_ids)
    for recipient in recipients:
        _notify_user(
            recipient,
            type="new_message",
            title="Nouveau message",
            body=message.body,
            conversation=conversation,
            message_id=message.id,
        )


def _notify_user(recipient, *, type, title, body, conversation, message_id=None):
    from notifications.services import notify

    if recipient is None:
        return
    data = {"conversation_id": conversation.id}
    if message_id is not None:
        data["message_id"] = message_id
    notify(
        recipient=recipient,
        type=type,
        title=title,
        body=body,
        data=data,
    )


def _photo_url(image, request):
    if not image:
        return None
    return request.build_absolute_uri(image.url)


def _display_name(user):
    name = f"{user.first_name} {user.last_name}".strip()
    return name or user.email


def _refuge_for_user(user):
    refuge = getattr(user, "refuge", None)
    if refuge is not None:
        return refuge
    return Refuge.objects.create(
        user=user,
        name=_display_name(user),
        phone=user.phone or "",
    )


def _refuge_card(refuge, request):
    photo = _photo_url(refuge.user.photo, request) or _photo_url(refuge.logo, request)
    return {
        "id": refuge.id,
        "name": refuge.name,
        "phone": refuge.phone or refuge.user.phone,
        "location": refuge.address or "",
        "photo": photo,
    }


def _vet_card(vet, request):
    profile = getattr(vet, "veterinaire_profile", None)
    name = _display_name(vet)
    return {
        "id": vet.id,
        "name": name,
        "phone": vet.phone,
        "location": (getattr(profile, "address", "") or "") if profile is not None else "",
        "photo": _photo_url(vet.photo, request),
    }
