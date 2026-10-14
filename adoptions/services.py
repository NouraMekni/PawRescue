from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.models import User
from animals.models import Animal
from notifications.models import Notification
from notifications.services import notify
from .models import AdoptionRequest

APPLICANT_ROLES = (User.Role.CITOYEN, User.Role.BENEVOLE)


def can_review(user, adoption):
    return (
        adoption.status == AdoptionRequest.Status.PENDING
        and user.pk != adoption.applicant_id
        and adoption.refuge_id == adoption.animal.refuge_id
        and (
            user.role == User.Role.ADMIN
            or (user.role == User.Role.REFUGE and adoption.refuge.user_id == user.pk)
        )
    )


def can_cancel(user, adoption):
    return (
        user.role in APPLICANT_ROLES
        and adoption.applicant_id == user.pk
        and adoption.status == AdoptionRequest.Status.PENDING
    )


@transaction.atomic
def create_adoption_request(*, applicant, animal, message=""):
    if applicant.role not in APPLICANT_ROLES:
        raise PermissionDenied("Seuls les citoyens et bénévoles peuvent envoyer une demande d'adoption.")
    animal = Animal.objects.select_for_update().get(pk=animal.pk)
    if animal.status != Animal.Status.IN_SHELTER or not animal.is_adoptable:
        raise ValidationError("Cet animal n'est pas disponible à l'adoption.")
    if animal.refuge_id is None:
        raise ValidationError("Cet animal n'est associé à aucun refuge.")
    if animal.refuge.user_id == applicant.pk:
        raise PermissionDenied("Vous ne pouvez pas demander l'adoption de votre propre animal.")
    if AdoptionRequest.objects.filter(animal=animal, applicant=applicant, status=AdoptionRequest.Status.PENDING).exists():
        raise ValidationError("Vous avez déjà une demande d'adoption en attente pour cet animal.")
    try:
        # Keep the outer transaction usable when the uniqueness constraint rejects a duplicate.
        with transaction.atomic():
            adoption = AdoptionRequest.objects.create(
                animal=animal, applicant=applicant, refuge=animal.refuge, message=message,
            )
    except IntegrityError as error:
        raise ValidationError("Vous avez déjà une demande d'adoption en attente pour cet animal.") from error
    name = applicant.get_full_name().strip() or applicant.username
    notify(
        recipient=animal.refuge.user, type=Notification.Type.ADOPTION_UPDATE,
        title="Nouvelle demande d’adoption", body=f"{name} souhaite adopter {animal.name}",
        data={"adoption_id": adoption.pk, "animal_id": animal.pk, "status": adoption.status},
    )
    return adoption


def _lock_request(adoption):
    # All transitions lock the animal first, then the request, to serialize competing decisions.
    animal = Animal.objects.select_for_update().get(pk=adoption.animal_id)
    locked = AdoptionRequest.objects.select_for_update().get(pk=adoption.pk)
    locked.animal = animal
    return locked


def _check_reviewer(reviewer, adoption):
    if reviewer.pk == adoption.applicant_id:
        raise PermissionDenied("Vous ne pouvez pas décider de votre propre demande.")
    if reviewer.role != User.Role.ADMIN and not (
        reviewer.role == User.Role.REFUGE
        and adoption.refuge.user_id == reviewer.pk
        and adoption.animal.refuge_id == adoption.refuge_id
    ):
        raise PermissionDenied("Vous ne pouvez pas gérer les demandes de ce refuge.")
    if adoption.refuge_id != adoption.animal.refuge_id:
        raise ValidationError("Le refuge de cet animal a changé. Cette demande ne peut plus être traitée.")
    if adoption.status != AdoptionRequest.Status.PENDING:
        raise ValidationError("Cette demande n'est plus en attente.")


def _save_decision(adoption, reviewer, status, note):
    adoption.status = status
    adoption.reviewed_by = reviewer
    adoption.review_note = note
    adoption.reviewed_at = timezone.now()
    adoption.save(update_fields=["status", "reviewed_by", "review_note", "reviewed_at"])
    accepted = status == AdoptionRequest.Status.APPROVED
    verb = "accepté" if accepted else "refusé"
    body = f"L’association {adoption.refuge.name} a {verb} votre demande d’adoption pour {adoption.animal.name}."
    if note == "Un autre candidat a été sélectionné.":
        body += " Un autre candidat a été sélectionné."
    notify(
        recipient=adoption.applicant, type=Notification.Type.ADOPTION_UPDATE,
        title="Demande acceptée" if accepted else "Demande refusée", body=body,
        data={"adoption_id": adoption.pk, "animal_id": adoption.animal_id, "status": status},
    )


@transaction.atomic
def approve_adoption_request(*, adoption_request, reviewer, review_note=""):
    adoption = _lock_request(adoption_request)
    _check_reviewer(reviewer, adoption)
    animal = adoption.animal
    if animal.status != Animal.Status.IN_SHELTER or not animal.is_adoptable:
        raise ValidationError("Cet animal n'est plus disponible à l'adoption.")
    _save_decision(adoption, reviewer, AdoptionRequest.Status.APPROVED, review_note)
    animal.status = Animal.Status.ADOPTED
    animal.is_adoptable = False
    animal.save(update_fields=["status", "is_adoptable", "updated_at"])
    others = adoption_queryset().filter(animal=animal, status=AdoptionRequest.Status.PENDING).exclude(pk=adoption.pk)
    for other in others:
        _save_decision(other, reviewer, AdoptionRequest.Status.REJECTED, "Un autre candidat a été sélectionné.")
    return adoption


@transaction.atomic
def reject_adoption_request(*, adoption_request, reviewer, review_note=""):
    adoption = _lock_request(adoption_request)
    _check_reviewer(reviewer, adoption)
    _save_decision(adoption, reviewer, AdoptionRequest.Status.REJECTED, review_note)
    return adoption


@transaction.atomic
def cancel_adoption_request(*, adoption_request, applicant):
    adoption = _lock_request(adoption_request)
    if applicant.role not in APPLICANT_ROLES or adoption.applicant_id != applicant.pk:
        raise PermissionDenied("Vous ne pouvez pas annuler cette demande.")
    if adoption.status != AdoptionRequest.Status.PENDING:
        raise ValidationError("Seules les demandes en attente peuvent être annulées.")
    adoption.status = AdoptionRequest.Status.CANCELLED
    adoption.save(update_fields=["status"])
    return adoption


def visible_adoptions(user):
    queryset = AdoptionRequest.objects.all()
    if user.role in APPLICANT_ROLES:
        return queryset.filter(applicant=user)
    if user.role == User.Role.REFUGE:
        return queryset.filter(refuge__user=user)
    if user.role == User.Role.ADMIN:
        return queryset
    return queryset.none()


def adoption_queryset():
    return AdoptionRequest.objects.select_related(
        "animal", "animal__species", "animal__refuge", "applicant", "refuge", "reviewed_by",
    ).prefetch_related("animal__photos")
