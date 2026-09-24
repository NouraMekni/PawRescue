from django.conf import settings
from django.db import models


class Species(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural = "species"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Animal(models.Model):
    class Sex(models.TextChoices):
        MALE = "M", "Mâle"
        FEMALE = "F", "Femelle"
        UNKNOWN = "unknown", "Inconnu"

    class Status(models.TextChoices):
        STRAY = "stray", "Errant"
        RESCUED = "rescued", "Secouru"
        IN_SHELTER = "in_shelter", "En refuge"
        RESERVED = "reserved", "Réservé"
        ADOPTED = "adopted", "Adopté"

    class Size(models.TextChoices):
        SMALL = "small", "Petit"
        MEDIUM = "medium", "Moyen"
        LARGE = "large", "Grand"

    refuge = models.ForeignKey(
        "shelters.Refuge",
        on_delete=models.CASCADE,
        related_name="animals",
    )
    source_report = models.OneToOneField(
        "reports.Report",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_animal",
    )
    name = models.CharField(max_length=100)
    species = models.ForeignKey(
        Species,
        on_delete=models.PROTECT,
        related_name="animals",
    )
    breed = models.CharField(max_length=100, blank=True)
    estimated_age_months = models.PositiveIntegerField(null=True, blank=True)
    sex = models.CharField(max_length=10, choices=Sex.choices, default=Sex.UNKNOWN)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    color = models.CharField(max_length=100, blank=True)
    behavior = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_SHELTER,
    )
    size = models.CharField(max_length=10, choices=Size.choices, blank=True)
    is_adoptable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.species})"


class AnimalPhoto(models.Model):
    animal = models.ForeignKey(
        Animal,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(upload_to="animals/photos/")
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Photo {self.animal.name} #{self.order}"


class MedicalRecord(models.Model):
    animal = models.OneToOneField(
        Animal,
        on_delete=models.CASCADE,
        related_name="medical_record",
    )
    allergies = models.TextField(blank=True)
    shelter_notes = models.TextField(blank=True)
    next_appointment = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dossier médical — {self.animal.name}"


class MedicalEntry(models.Model):
    class EntryType(models.TextChoices):
        DIAGNOSIS = "diagnosis", "Diagnostic"
        TREATMENT = "treatment", "Traitement"
        VACCINE = "vaccine", "Vaccin"
        SURGERY = "surgery", "Opération"
        NOTE = "note", "Remarque"

    medical_record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField()
    next_due_date = models.DateField(null=True, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medical_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name_plural = "medical entries"

    def __str__(self):
        return f"{self.get_entry_type_display()}: {self.title}"
