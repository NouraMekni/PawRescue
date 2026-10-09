from django.db import transaction
from rest_framework import serializers

from animals.models import Animal, AnimalPhoto
from .models import AdoptionRequest


class AdoptionAnimalPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalPhoto
        fields = [
            "id",
            "image",
            "is_primary",
            "order",
        ]


class AdoptionAnimalSerializer(serializers.ModelSerializer):
    photos = AdoptionAnimalPhotoSerializer(
        many=True,
        read_only=True,
    )

    species_name = serializers.CharField(
        source="species.name",
        read_only=True,
    )

    refuge_name = serializers.CharField(
        source="refuge.name",
        read_only=True,
    )

    class Meta:
        model = Animal
        fields = [
            "id",
            "name",
            "species",
            "species_name",
            "breed",
            "estimated_age_months",
            "sex",
            "weight_kg",
            "color",
            "behavior",
            "status",
            "size",
            "is_adoptable",
            "refuge",
            "refuge_name",
            "photos",
        ]


class AdoptionRequestSerializer(serializers.ModelSerializer):
    animal_details = AdoptionAnimalSerializer(
        source="animal",
        read_only=True,
    )

    applicant_username = serializers.CharField(
        source="applicant.username",
        read_only=True,
    )

    refuge_name = serializers.CharField(
        source="refuge.name",
        read_only=True,
    )

    reviewed_by_username = serializers.CharField(
        source="reviewed_by.username",
        read_only=True,
        allow_null=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = AdoptionRequest
        fields = [
            "id",
            "animal",
            "animal_details",
            "applicant",
            "applicant_username",
            "refuge",
            "refuge_name",
            "message",
            "status",
            "status_display",
            "reviewed_by",
            "reviewed_by_username",
            "review_note",
            "created_at",
            "reviewed_at",
        ]

        read_only_fields = [
            "applicant",
            "refuge",
            "status",
            "reviewed_by",
            "review_note",
            "created_at",
            "reviewed_at",
        ]


class AdoptionRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdoptionRequest
        fields = [
            "animal",
            "message",
        ]

    def validate_animal(self, animal):
        """
        An animal can only receive an adoption request when:

        - it is inside a shelter
        - it is marked as adoptable
        """

        if animal.status != Animal.Status.IN_SHELTER:
            raise serializers.ValidationError(
                "Cet animal n'est pas actuellement en refuge."
            )

        if not animal.is_adoptable:
            raise serializers.ValidationError(
                "Cet animal n'est pas disponible à l'adoption."
            )

        return animal

    def validate(self, attrs):
        request = self.context["request"]
        animal = attrs["animal"]

        # The applicant must be different from the refuge if
        # the same user somehow has access to the animal.
        if animal.refuge is None:
            raise serializers.ValidationError(
                "Cet animal n'est associé à aucun refuge."
            )

        # Prevent duplicate pending requests.
        already_pending = AdoptionRequest.objects.filter(
            animal=animal,
            applicant=request.user,
            status=AdoptionRequest.Status.PENDING,
        ).exists()

        if already_pending:
            raise serializers.ValidationError(
                "Vous avez déjà une demande d'adoption en attente pour cet animal."
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]

        animal = validated_data["animal"]

        adoption = AdoptionRequest.objects.create(
            animal=animal,
            applicant=request.user,
            refuge=animal.refuge,
            message=validated_data.get("message", ""),
            status=AdoptionRequest.Status.PENDING,
        )

        return adoption


class AdoptionReviewSerializer(serializers.Serializer):
    """
    Used when a refuge approves or rejects an adoption request.

    The status is NOT received from the frontend.
    The endpoint itself decides whether the action is approve/reject.
    """

    review_note = serializers.CharField(
        required=False,
        allow_blank=True,
    )