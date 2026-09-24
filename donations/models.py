from django.conf import settings
from django.db import models


class Donation(models.Model):
    class Type(models.TextChoices):
        ONE_TIME = "one_time", "Don ponctuel"
        SPONSORSHIP = "sponsorship", "Parrainage"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        CONFIRMED = "confirmed", "Confirmé"
        FAILED = "failed", "Échoué"

    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="donations",
    )
    refuge = models.ForeignKey(
        "shelters.Refuge",
        on_delete=models.CASCADE,
        related_name="donations",
    )
    animal = models.ForeignKey(
        "animals.Animal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donations",
        help_text="Renseigné pour un parrainage d'animal",
    )
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.ONE_TIME)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="TND")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    payment_ref = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Don {self.amount} {self.currency} → {self.refuge}"
