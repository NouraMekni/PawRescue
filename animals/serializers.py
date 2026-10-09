from rest_framework import serializers

from .models import (
    Animal,
    AnimalPhoto,
    MedicalRecord,
    MedicalEntry,
)


class SpeciesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Animal.species.field.related_model
        fields = [
            "id",
            "name",
            "icon",
        ]


class AnimalPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalPhoto
        fields = [
            "id",
            "image",
            "is_primary",
            "order",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]


class AnimalListSerializer(serializers.ModelSerializer):
    species_name = serializers.CharField(
        source="species.name",
        read_only=True,
    )

    species_icon = serializers.CharField(
        source="species.icon",
        read_only=True,
    )

    refuge_name = serializers.CharField(
        source="refuge.name",
        read_only=True,
    )

    primary_photo = serializers.SerializerMethodField()

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    sex_display = serializers.CharField(
        source="get_sex_display",
        read_only=True,
    )

    size_display = serializers.CharField(
        source="get_size_display",
        read_only=True,
    )

    class Meta:
        model = Animal
        fields = [
            "id",
            "name",

            "species",
            "species_name",
            "species_icon",

            "breed",
            "estimated_age_months",
            "sex",
            "sex_display",
            "weight_kg",
            "color",
            "behavior",
            "size",
            "size_display",

            "status",
            "status_display",
            "is_adoptable",

            "refuge",
            "refuge_name",

            "primary_photo",

            "created_at",
            "updated_at",
        ]

    def get_primary_photo(self, obj):
        photo = obj.photos.filter(
            is_primary=True
        ).first()

        if photo is None:
            photo = obj.photos.first()

        if photo is None:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(
                photo.image.url
            )

        return photo.image.url


class AnimalDetailSerializer(serializers.ModelSerializer):
    species_name = serializers.CharField(
        source="species.name",
        read_only=True,
    )

    species_icon = serializers.CharField(
        source="species.icon",
        read_only=True,
    )

    refuge_name = serializers.CharField(
        source="refuge.name",
        read_only=True,
    )

    photos = AnimalPhotoSerializer(
        many=True,
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    sex_display = serializers.CharField(
        source="get_sex_display",
        read_only=True,
    )

    size_display = serializers.CharField(
        source="get_size_display",
        read_only=True,
    )

    class Meta:
        model = Animal
        fields = [
            "id",
            "name",

            "species",
            "species_name",
            "species_icon",

            "breed",
            "estimated_age_months",
            "sex",
            "sex_display",

            "weight_kg",
            "color",
            "behavior",

            "size",
            "size_display",

            "status",
            "status_display",

            "is_adoptable",

            "refuge",
            "refuge_name",

            "source_report",

            "photos",

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class AnimalCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Animal
        fields = [
            "name",
            "species",
            "breed",
            "estimated_age_months",
            "sex",
            "weight_kg",
            "color",
            "behavior",
            "status",
            "size",
            "refuge",
            "source_report",
            "is_adoptable",
        ]

    def validate(self, attrs):
        status = attrs.get(
            "status",
            Animal.Status.IN_SHELTER,
        )

        is_adoptable = attrs.get(
            "is_adoptable",
            False,
        )

        refuge = attrs.get("refuge")

        # An adoptable animal must be in a refuge.
        if is_adoptable:

            if status != Animal.Status.IN_SHELTER:
                raise serializers.ValidationError(
                    {
                        "is_adoptable": (
                            "Un animal disponible à "
                            "l'adoption doit être "
                            "dans un refuge."
                        )
                    }
                )

            if refuge is None:
                raise serializers.ValidationError(
                    {
                        "refuge": (
                            "Un animal disponible à "
                            "l'adoption doit être "
                            "associé à un refuge."
                        )
                    }
                )

        # An adopted animal cannot remain adoptable.
        if status == Animal.Status.ADOPTED:
            if is_adoptable:
                raise serializers.ValidationError(
                    {
                        "is_adoptable": (
                            "Un animal adopté ne peut "
                            "pas être disponible à l'adoption."
                        )
                    }
                )

        return attrs


class AnimalUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Animal
        fields = [
            "name",
            "species",
            "breed",
            "estimated_age_months",
            "sex",
            "weight_kg",
            "color",
            "behavior",
            "status",
            "size",
            "refuge",
            "is_adoptable",
        ]

    def validate(self, attrs):

        instance = self.instance

        status = attrs.get(
            "status",
            instance.status,
        )

        is_adoptable = attrs.get(
            "is_adoptable",
            instance.is_adoptable,
        )

        refuge = attrs.get(
            "refuge",
            instance.refuge,
        )

        if is_adoptable:

            if status != Animal.Status.IN_SHELTER:
                raise serializers.ValidationError(
                    {
                        "is_adoptable": (
                            "Un animal disponible à "
                            "l'adoption doit être "
                            "dans un refuge."
                        )
                    }
                )

            if refuge is None:
                raise serializers.ValidationError(
                    {
                        "refuge": (
                            "Un animal disponible à "
                            "l'adoption doit être "
                            "associé à un refuge."
                        )
                    }
                )

        if status == Animal.Status.ADOPTED:
            if is_adoptable:
                raise serializers.ValidationError(
                    {
                        "is_adoptable": (
                            "Un animal adopté ne peut "
                            "pas être disponible à l'adoption."
                        )
                    }
                )

        return attrs


class MedicalEntrySerializer(serializers.ModelSerializer):
    entry_type_display = serializers.CharField(
        source="get_entry_type_display",
        read_only=True,
    )

    performed_by_username = serializers.CharField(
        source="performed_by.username",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = MedicalEntry
        fields = [
            "id",
            "entry_type",
            "entry_type_display",
            "title",
            "description",
            "date",
            "next_due_date",
            "performed_by",
            "performed_by_username",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "performed_by",
            "created_at",
        ]


class MedicalRecordSerializer(serializers.ModelSerializer):
    entries = MedicalEntrySerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = MedicalRecord
        fields = [
            "id",
            "animal",
            "allergies",
            "shelter_notes",
            "next_appointment",
            "entries",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "animal",
            "updated_at",
        ]