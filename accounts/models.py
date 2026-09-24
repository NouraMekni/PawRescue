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

    def __str__(self):
        return f"{self.username} ({self.role})"
