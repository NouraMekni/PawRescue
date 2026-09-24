from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        NEW_EMERGENCY = "new_emergency", "Nouvelle urgence"
        MISSION_ASSIGNED = "mission_assigned", "Mission assignée"
        ADOPTION_UPDATE = "adoption_update", "Mise à jour adoption"
        VACCINE_REMINDER = "vaccine_reminder", "Rappel vaccin"
        NEW_MESSAGE = "new_message", "Nouveau message"
        NEW_REPORT = "new_report", "Nouveau signalement"
        OTHER = "other", "Autre"

    class Channel(models.TextChoices):
        PUSH = "push", "Push"
        IN_APP = "in_app", "In-app"
        BOTH = "both", "Les deux"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=30, choices=Type.choices, default=Type.OTHER)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
        default=Channel.BOTH,
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} → {self.recipient}"
