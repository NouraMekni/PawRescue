from django.conf import settings
from django.db import models


class Mission(models.Model):
    class Type(models.TextChoices):
        RESCUE = "rescue", "Secours"
        TRANSPORT = "transport", "Transport"
        MEDICAL_EMERGENCY = "medical_emergency", "Urgence médicale"

    class Status(models.TextChoices):
        OPEN = "open", "Ouverte"
        ACCEPTED = "accepted", "Prise en charge"
        EN_ROUTE = "en_route", "En route"
        ON_SITE = "on_site", "Intervention"
        COMPLETED = "completed", "Animal secouru"
        CANCELLED = "cancelled", "Annulée"

    report = models.OneToOneField(
        "reports.Report",
        on_delete=models.CASCADE,
        related_name="mission",
    )
    refuge = models.ForeignKey(
        "shelters.Refuge",
        on_delete=models.CASCADE,
        related_name="missions",
    )
    type = models.CharField(max_length=30, choices=Type.choices, default=Type.RESCUE)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    assigned_benevole = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="missions_as_benevole",
    )
    assigned_veterinaire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="missions_as_veterinaire",
    )
    target_latitude = models.FloatField()
    target_longitude = models.FloatField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Mission #{self.pk} — {self.get_status_display()}"


class MissionStatusHistory(models.Model):
    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    status = models.CharField(max_length=20, choices=Mission.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mission_status_changes",
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "mission status histories"

    def __str__(self):
        return f"Mission #{self.mission_id} → {self.status}"


class MissionResponse(models.Model):
    class Response(models.TextChoices):
        ACCEPTED = "accepted", "Acceptée"
        REFUSED = "refused", "Refusée"

    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mission_responses",
    )
    response = models.CharField(max_length=20, choices=Response.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("mission", "user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} {self.response} mission #{self.mission_id}"
