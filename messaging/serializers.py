from django.contrib.auth import get_user_model
from rest_framework import serializers

from shelters.models import Refuge

from .models import Conversation, Message
from .services import other_user

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "sender", "body", "is_read", "created_at")
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    refuge_name = serializers.SerializerMethodField()
    veterinaire_name = serializers.SerializerMethodField()
    participant_name = serializers.SerializerMethodField()
    needs_response = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = (
            "id",
            "status",
            "refuge",
            "refuge_name",
            "veterinaire",
            "veterinaire_name",
            "participant",
            "participant_name",
            "requested_by",
            "blocked_by",
            "report",
            "animal",
            "needs_response",
            "photo",
            "last_message",
            "messages",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_refuge_name(self, conversation):
        if conversation.refuge_id is None:
            return None
        return conversation.refuge.name

    def get_veterinaire_name(self, conversation):
        return _person_name(conversation.veterinaire)

    def get_participant_name(self, conversation):
        return _person_name(conversation.participant)

    def get_photo(self, conversation):
        request = self.context.get("request")
        if request is None:
            return None
        other = other_user(request.user, conversation)
        if other is None:
            return None
        photo = _media_url(getattr(other, "photo", None), request)
        refuge = conversation.refuge
        if photo is None and refuge is not None and other.id == refuge.user_id:
            photo = _media_url(refuge.logo, request)
        return photo

    def get_needs_response(self, conversation):
        user = self.context["request"].user
        return (
            conversation.status == Conversation.Status.PENDING
            and conversation.requested_by_id != user.id
        )

    def get_last_message(self, conversation):
        message = conversation.messages.order_by("-created_at").first()
        if message is None:
            return None
        return MessageSerializer(message).data


class ConversationCreateSerializer(serializers.Serializer):
    refuge = serializers.PrimaryKeyRelatedField(
        queryset=Refuge.objects.all(),
        required=False,
    )
    veterinaire = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.VETERINAIRE),
        required=False,
    )
    participant = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
    )
    report = serializers.IntegerField(required=False, allow_null=True)
    animal = serializers.IntegerField(required=False, allow_null=True)
    body = serializers.CharField()

    def validate_body(self, value):
        text = value.strip()
        if not text:
            raise serializers.ValidationError("Le message ne peut pas être vide.")
        return text


def _media_url(image, request):
    if not image:
        return None
    return request.build_absolute_uri(image.url)


def _person_name(user):
    if user is None:
        return None
    name = f"{user.first_name} {user.last_name}".strip()
    return name or user.email


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField()

    def validate_body(self, value):
        text = value.strip()
        if not text:
            raise serializers.ValidationError("Le message ne peut pas être vide.")
        return text
