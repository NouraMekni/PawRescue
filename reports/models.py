from django.conf import settings
from django.db import models


class Report(models.Model):
    class Type(models.TextChoices):
        STRAY = "stray", "Animal errant"
        INJURED = "injured", "Animal blessé"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        ASSIGNED = "assigned", "Assigné"
        IN_PROGRESS = "in_progress", "En cours"
        RESCUED = "rescued", "Secouru"
        CLOSED = "closed", "Clôturé"
        REJECTED = "rejected", "Rejeté"

    class Severity(models.TextChoices):
        MILD = "mild", "Léger"
        MODERATE = "moderate", "Modéré"
        CRITICAL = "critical", "Critique"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    species = models.ForeignKey(
        "animals.Species",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )
    description = models.TextField(blank=True)
    estimated_presence = models.CharField(max_length=100, blank=True)
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        blank=True,
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    address_text = models.CharField(max_length=255, blank=True)
    assigned_refuge = models.ForeignKey(
        "shelters.Refuge",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report #{self.pk} ({self.get_type_display()}) — {self.status}"


class ReportPhoto(models.Model):
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(upload_to="reports/photos/")
    taken_at = models.DateTimeField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Photo report #{self.report_id} #{self.order}"
