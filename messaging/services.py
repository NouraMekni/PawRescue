from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q

from .models import Conversation, UserBlock


def party_user_ids(conversation):
    ids = {conversation.participant_id}
    if conversation.refuge_id:
        ids.add(conversation.refuge.user_id)
    if conversation.veterinaire_id:
        ids.add(conversation.veterinaire_id)
    return ids


def is_party(user, conversation):
    return user.id in party_user_ids(conversation)


def counterparty_of_participant(conversation):
    if conversation.refuge_id:
        return conversation.refuge.user
    return conversation.veterinaire


def other_user(user, conversation):
    if user.id != conversation.participant_id:
        return conversation.participant
    if conversation.refuge_id:
        return conversation.refuge.user
    return conversation.veterinaire


def is_blocked(user_a, user_b):
    return UserBlock.objects.filter(
        Q(blocker=user_a, blocked=user_b) | Q(blocker=user_b, blocked=user_a)
    ).exists()


def find_conversation(participant, report, refuge=None, veterinaire=None):
    queryset = Conversation.objects.filter(participant=participant)
    if refuge is not None:
        queryset = queryset.filter(refuge=refuge)
    else:
        queryset = queryset.filter(refuge__isnull=True, veterinaire=veterinaire)
    if report is None:
        queryset = queryset.filter(report__isnull=True)
    else:
        queryset = queryset.filter(report=report)
    return queryset.first()


def push_to_users(user_ids, payload):
    layer = get_channel_layer()
    if layer is None:
        return
    for user_id in user_ids:
        async_to_sync(layer.group_send)(
            f"user-{user_id}",
            {"type": "conversation.event", "payload": payload},
        )
