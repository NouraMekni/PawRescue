from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import (
    Animal,
    AnimalPhoto,
    MedicalRecord,
    MedicalEntry,
)


@transaction.atomic
def create_animal(
    *,
    creator,
    validated_data,
):
    """
    Create a new animal.

    Any authenticated role can create an animal.

    An animal can be created as adoptable, but when
    is_adoptable=True it must:
        - be in a shelter
        - have a refuge
    """

    animal = Animal.objects.create(
        **validated_data
    )

    return animal


@transaction.atomic
def update_animal(
    *,
    animal,
    validated_data,
):
    """
    Update an animal.
    """

    for field, value in validated_data.items():
        setattr(
            animal,
            field,
            value,
        )

    animal.save()

    return animal


@transaction.atomic
def delete_animal(
    *,
    animal,
):
    """
    Delete an animal.
    """

    animal.delete()


def animal_queryset():
    """
    Optimized queryset for animals.
    """

    return (
        Animal.objects
        .select_related(
            "species",
            "refuge",
            "source_report",
        )
        .prefetch_related(
            "photos",
        )
    )


def adoptable_animals_queryset():
    """
    Return animals currently available for adoption.
    """

    return (
        animal_queryset()
        .filter(
            status=Animal.Status.IN_SHELTER,
            is_adoptable=True,
        )
    )


def get_animal_for_adoption(
    *,
    animal_id,
):
    """
    Return an animal that is currently available
    for adoption.
    """

    try:
        return adoptable_animals_queryset().get(
            pk=animal_id
        )
    except Animal.DoesNotExist:
        raise ValidationError(
            "Cet animal n'est pas disponible à l'adoption."
        )


@transaction.atomic
def set_animal_adoptable(
    *,
    animal,
):
    """
    Make an animal available for adoption.
    """

    if animal.refuge is None:
        raise ValidationError(
            "L'animal doit être associé à un refuge."
        )

    if animal.status != Animal.Status.IN_SHELTER:
        raise ValidationError(
            "L'animal doit être dans un refuge "
            "pour être disponible à l'adoption."
        )

    animal.is_adoptable = True

    animal.save(
        update_fields=[
            "is_adoptable",
            "updated_at",
        ]
    )

    return animal


@transaction.atomic
def remove_animal_from_adoption(
    *,
    animal,
):
    """
    Remove an animal from adoption availability.

    Existing pending adoption requests are not
    automatically deleted here.
    """

    animal.is_adoptable = False

    animal.save(
        update_fields=[
            "is_adoptable",
            "updated_at",
        ]
    )

    return animal


@transaction.atomic
def add_animal_photo(
    *,
    animal,
    image,
    is_primary=False,
    order=0,
):
    """
    Add a photo to an animal.
    """

    if is_primary:
        AnimalPhoto.objects.filter(
            animal=animal,
            is_primary=True,
        ).update(
            is_primary=False
        )

    return AnimalPhoto.objects.create(
        animal=animal,
        image=image,
        is_primary=is_primary,
        order=order,
    )


@transaction.atomic
def create_medical_record(
    *,
    animal,
    allergies="",
    shelter_notes="",
    next_appointment=None,
):
    """
    Create the medical record for an animal.
    """

    if MedicalRecord.objects.filter(
        animal=animal
    ).exists():
        raise ValidationError(
            "Cet animal possède déjà un dossier médical."
        )

    return MedicalRecord.objects.create(
        animal=animal,
        allergies=allergies,
        shelter_notes=shelter_notes,
        next_appointment=next_appointment,
    )


@transaction.atomic
def add_medical_entry(
    *,
    medical_record,
    performed_by,
    validated_data,
):
    """
    Add a medical entry to an animal's record.
    """

    return MedicalEntry.objects.create(
        medical_record=medical_record,
        performed_by=performed_by,
        **validated_data,
    )