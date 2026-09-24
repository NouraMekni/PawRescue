from django.conf import settings
from django.db import models


class Refuge(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="refuge",
    )
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    phone = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(default=0)
    action_radius_km = models.FloatField(default=20.0)
    is_verified = models.BooleanField(default=False)
    logo = models.ImageField(upload_to="refuges/logos/", blank=True, null=True)
    accepted_species = models.ManyToManyField(
        "animals.Species",
        blank=True,
        related_name="refuges",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class RefugeMembership(models.Model):
    class MemberType(models.TextChoices):
        BENEVOLE = "benevole", "Bénévole"
        VETERINAIRE = "veterinaire", "Vétérinaire"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        ACTIVE = "active", "Actif"
        REVOKED = "revoked", "Révoqué"

    refuge = models.ForeignKey(
        Refuge,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="refuge_memberships",
    )
    member_type = models.CharField(max_length=20, choices=MemberType.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("refuge", "user")
        ordering = ["-joined_at"]

    def __str__(self):
        return f"{self.user} @ {self.refuge} ({self.member_type})"
