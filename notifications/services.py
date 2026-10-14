from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from .models import Notification
from .serializers import NotificationSerializer


def notify(*, recipient, type, title, body="", data=None):
    """Create an in-app notification and push it to that user's open socket.

    Other actions can call this with their own type, title, and data.
    """
    notification = Notification.objects.create(
        recipient=recipient,
        type=type,
        title=title,
        body=body,
        data=data or {},
        channel=Notification.Channel.IN_APP,
    )
    def broadcast():
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            f"user-{recipient.id}",
            {
                "type": "notification.event",
                "payload": {
                    "type": "notification.created",
                    "notification": NotificationSerializer(notification).data,
                },
            },
        )
    transaction.on_commit(broadcast, robust=True)
    return notification
