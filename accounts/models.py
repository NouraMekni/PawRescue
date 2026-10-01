from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CITOYEN = "citoyen", "Citoyen"
        BENEVOLE = "benevole", "Bénévole"
        VETERINAIRE = "veterinaire", "Vétérinaire"
        REFUGE = "refuge", "Refuge"
        ADMIN = "admin", "Administrateur"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CITOYEN,
    )
    phone = models.CharField(max_length=20, blank=True)
    fcm_token = models.CharField(max_length=255, blank=True)
    photo = models.ImageField(upload_to="users/photos/", blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class CitoyenProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="citoyen_profile",
    )
    address = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Citoyen: {self.user.username}"


class BenevoleProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="benevole_profile",
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    max_missions = models.PositiveIntegerField(default=3)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"Bénévole: {self.user.username}"


class VeterinaireProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "En attente"
        APPROVED = "approved", "Approuvé"
        REJECTED = "rejected", "Refusé"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="veterinaire_profile",
    )
    license_number = models.CharField(max_length=100, blank=True)
    governorate = models.CharField(max_length=50, blank=True)
    clinic_name = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=255, blank=True)
    verification_document = models.FileField(
        upload_to="veterinaires/documents/",
        blank=True,
        null=True,
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    specialties = models.TextField(blank=True)
    radius_km = models.FloatField(default=15.0)

    def __str__(self):
        return f"Vétérinaire: {self.user.username}"
