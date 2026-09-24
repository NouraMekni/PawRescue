from django.conf import settings
from django.db import models


class AdoptionRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        APPROVED = "approved", "Approuvée"
        REJECTED = "rejected", "Refusée"
        CANCELLED = "cancelled", "Annulée"

    animal = models.ForeignKey(
        "animals.Animal",
        on_delete=models.CASCADE,
        related_name="adoption_requests",
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="adoption_requests",
    )
    refuge = models.ForeignKey(
        "shelters.Refuge",
        on_delete=models.CASCADE,
        related_name="adoption_requests",
    )
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_adoptions",
    )
    review_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["animal", "applicant"],
                condition=models.Q(status="pending"),
                name="unique_pending_adoption_per_animal_applicant",
            )
        ]

    def __str__(self):
        return f"Adoption {self.animal} par {self.applicant} ({self.status})"
