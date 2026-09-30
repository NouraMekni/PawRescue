from django.db import transaction
from rest_framework import serializers

from .models import Report, ReportPhoto
from .services import nearest_refuges


class PhotosField(serializers.ListField):
    child = serializers.ImageField()

    def get_value(self, dictionary):
        if hasattr(dictionary, "getlist"):
            files = dictionary.getlist(self.field_name)
            if files:
                return files
        return super().get_value(dictionary)


class ReportPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportPhoto
        fields = ("id", "image", "order", "taken_at")


class NearestRefugeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    distance_km = serializers.FloatField()


class ReportSerializer(serializers.ModelSerializer):
    photos = ReportPhotoSerializer(many=True, read_only=True)
    nearest_refuges = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            "id",
            "reporter",
            "type",
            "status",
            "species",
            "description",
            "estimated_presence",
            "severity",
            "latitude",
            "longitude",
            "address_text",
            "assigned_refuge",
            "photos",
            "nearest_refuges",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_nearest_refuges(self, report):
        ranked = nearest_refuges(
            report.latitude,
            report.longitude,
            species=report.species,
            limit=5,
        )
        return NearestRefugeSerializer(
            [
                {
                    "id": refuge.id,
                    "name": refuge.name,
                    "latitude": refuge.latitude,
                    "longitude": refuge.longitude,
                    "distance_km": round(distance, 2),
                }
                for distance, refuge in ranked
            ],
            many=True,
        ).data


class ReportCreateSerializer(serializers.ModelSerializer):
    photos = PhotosField(write_only=True, allow_empty=False)

    class Meta:
        model = Report
        fields = (
            "type",
            "species",
            "description",
            "estimated_presence",
            "severity",
            "latitude",
            "longitude",
            "address_text",
            "photos",
        )

    def validate(self, attrs):
        if attrs["type"] == Report.Type.INJURED and not attrs.get("severity"):
            raise serializers.ValidationError(
                {"severity": "La gravité est obligatoire pour un animal blessé."}
            )
        if attrs["type"] == Report.Type.STRAY:
            attrs["severity"] = ""
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        photos = validated_data.pop("photos")
        request = self.context["request"]
        ranked = nearest_refuges(
            validated_data["latitude"],
            validated_data["longitude"],
            species=validated_data.get("species"),
            limit=1,
        )
        assigned = ranked[0][1] if ranked else None
        report = Report.objects.create(
            reporter=request.user,
            assigned_refuge=assigned,
            status=Report.Status.ASSIGNED if assigned else Report.Status.PENDING,
            **validated_data,
        )
        for index, image in enumerate(photos):
            ReportPhoto.objects.create(report=report, image=image, order=index)
        return report
