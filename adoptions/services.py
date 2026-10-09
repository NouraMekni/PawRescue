from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import User
from animals.models import Animal

from .models import AdoptionRequest


def create_adoption_request(
    *,
    applicant,
    animal,
    message="",
):
    """
    Create a new adoption request.

    Rules:
    - applicant must be authenticated
    - animal must be in a shelter
    - animal must be adoptable
    - applicant cannot have another pending request
      for the same animal
    """

    if applicant.role != User.Role.CITOYEN:
        raise ValidationError(
            "Seuls les citoyens peuvent envoyer une demande d'adoption."
        )

    # Lock the animal while checking availability.
    animal = Animal.objects.select_for_update().select_related(
        "refuge"
    ).get(pk=animal.pk)

    if animal.status != Animal.Status.IN_SHELTER:
        raise ValidationError(
            "Cet animal n'est pas actuellement en refuge."
        )

    if not animal.is_adoptable:
        raise ValidationError(
            "Cet animal n'est pas disponible à l'adoption."
        )

    if animal.refuge is None:
        raise ValidationError(
            "Cet animal n'est associé à aucun refuge."
        )

    existing_request = AdoptionRequest.objects.filter(
        animal=animal,
        applicant=applicant,
        status=AdoptionRequest.Status.PENDING,
    ).exists()

    if existing_request:
        raise ValidationError(
            "Vous avez déjà une demande d'adoption en attente "
            "pour cet animal."
        )

    adoption = AdoptionRequest.objects.create(
        animal=animal,
        applicant=applicant,
        refuge=animal.refuge,
        message=message,
        status=AdoptionRequest.Status.PENDING,
    )

    return adoption


@transaction.atomic
def approve_adoption_request(
    *,
    adoption_request,
    reviewer,
    review_note="",
):
    """
    Approve an adoption request.

    Rules:
    - reviewer must be a refuge
    - reviewer must belong to the request's refuge
    - request must still be pending
    - animal must still be available
    - selected request becomes APPROVED
    - animal becomes ADOPTED
    - animal becomes non-adoptable
    - all other pending requests become REJECTED
    """

    if reviewer.role not in (
        User.Role.REFUGE,
        User.Role.ADMIN,
    ):
        raise ValidationError(
            "Vous n'avez pas le droit d'approuver cette demande."
        )

    adoption_request = (
        AdoptionRequest.objects
        .select_for_update()
        .select_related(
            "animal",
            "refuge",
            "applicant",
        )
        .get(pk=adoption_request.pk)
    )

    if adoption_request.status != AdoptionRequest.Status.PENDING:
        raise ValidationError(
            "Cette demande n'est plus en attente."
        )

    animal = (
        Animal.objects
        .select_for_update()
        .select_related("refuge")
        .get(pk=adoption_request.animal_id)
    )

    # Refuge users must belong to the same refuge.
    if reviewer.role == User.Role.REFUGE:
        reviewer_refuge = getattr(reviewer, "refuge", None)

        if reviewer_refuge is None:
            raise ValidationError(
                "Votre compte n'est associé à aucun refuge."
            )

        if reviewer_refuge.pk != animal.refuge_id:
            raise ValidationError(
                "Vous ne pouvez pas gérer les demandes "
                "d'un autre refuge."
            )

    # Admin can manage everything.

    if animal.status != Animal.Status.IN_SHELTER:
        raise ValidationError(
            "Cet animal n'est plus disponible dans le refuge."
        )

    if not animal.is_adoptable:
        raise ValidationError(
            "Cet animal n'est plus disponible à l'adoption."
        )

    # Approve selected request.
    adoption_request.status = AdoptionRequest.Status.APPROVED
    adoption_request.reviewed_by = reviewer
    adoption_request.review_note = review_note
    adoption_request.reviewed_at = timezone.now()
    adoption_request.save(
        update_fields=[
            "status",
            "reviewed_by",
            "review_note",
            "reviewed_at",
        ]
    )

    # Animal is now adopted.
    animal.status = Animal.Status.ADOPTED
    animal.is_adoptable = False
    animal.save(
        update_fields=[
            "status",
            "is_adoptable",
            "updated_at",
        ]
    )

    # Reject all other pending applications.
    AdoptionRequest.objects.filter(
        animal=animal,
        status=AdoptionRequest.Status.PENDING,
    ).exclude(
        pk=adoption_request.pk
    ).update(
        status=AdoptionRequest.Status.REJECTED,
        reviewed_by=reviewer,
        review_note="Un autre candidat a été sélectionné.",
        reviewed_at=timezone.now(),
    )

    return adoption_request


@transaction.atomic
def reject_adoption_request(
    *,
    adoption_request,
    reviewer,
    review_note="",
):
    """
    Reject an adoption request.
    """

    if reviewer.role not in (
        User.Role.REFUGE,
        User.Role.ADMIN,
    ):
        raise ValidationError(
            "Vous n'avez pas le droit de refuser cette demande."
        )

    adoption_request = (
        AdoptionRequest.objects
        .select_for_update()
        .select_related(
            "animal",
            "refuge",
        )
        .get(pk=adoption_request.pk)
    )

    if adoption_request.status != AdoptionRequest.Status.PENDING:
        raise ValidationError(
            "Cette demande n'est plus en attente."
        )

    if reviewer.role == User.Role.REFUGE:
        reviewer_refuge = getattr(reviewer, "refuge", None)

        if reviewer_refuge is None:
            raise ValidationError(
                "Votre compte n'est associé à aucun refuge."
            )

        if reviewer_refuge.pk != adoption_request.refuge_id:
            raise ValidationError(
                "Vous ne pouvez pas gérer les demandes "
                "d'un autre refuge."
            )

    adoption_request.status = AdoptionRequest.Status.REJECTED
    adoption_request.reviewed_by = reviewer
    adoption_request.review_note = review_note
    adoption_request.reviewed_at = timezone.now()

    adoption_request.save(
        update_fields=[
            "status",
            "reviewed_by",
            "review_note",
            "reviewed_at",
        ]
    )

    return adoption_request


@transaction.atomic
def cancel_adoption_request(
    *,
    adoption_request,
    applicant,
):
    """
    Cancel an adoption request.

    Only the applicant who created the request can cancel it.
    Only PENDING requests can be cancelled.
    """

    adoption_request = (
        AdoptionRequest.objects
        .select_for_update()
        .get(pk=adoption_request.pk)
    )

    if adoption_request.applicant_id != applicant.id:
        raise ValidationError(
            "Vous ne pouvez pas annuler cette demande."
        )

    if adoption_request.status != AdoptionRequest.Status.PENDING:
        raise ValidationError(
            "Seules les demandes en attente peuvent être annulées."
        )

    adoption_request.status = AdoptionRequest.Status.CANCELLED
    adoption_request.save(
        update_fields=["status"]
    )

    return adoption_request


def visible_adoptions(user):
    """
    Return the adoption requests visible to a user.

    Citizen:
        only their own requests.

    Refuge:
        requests belonging to their refuge.

    Admin:
        all requests.

    Other roles:
        no access.
    """

    queryset = AdoptionRequest.objects.all()

    if user.role == User.Role.CITOYEN:
        return queryset.filter(
            applicant=user
        )

    if user.role == User.Role.REFUGE:
        refuge = getattr(user, "refuge", None)

        if refuge is None:
            return queryset.none()

        return queryset.filter(
            refuge=refuge
        )

    if user.role == User.Role.ADMIN:
        return queryset

    return queryset.none()


def adoption_queryset():
    """
    Optimized queryset for adoption requests.
    """

    return (
        AdoptionRequest.objects
        .select_related(
            "animal",
            "animal__species",
            "animal__refuge",
            "applicant",
            "refuge",
            "reviewed_by",
        )
        .prefetch_related(
            "animal__photos",
        )
    )