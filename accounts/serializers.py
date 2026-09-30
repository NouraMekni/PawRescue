import os

from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from animals.models import Species
from shelters.models import Refuge

from .models import BenevoleProfile, CitoyenProfile, User, VeterinaireProfile

PUBLIC_ROLES = (
    User.Role.CITOYEN,
    User.Role.BENEVOLE,
    User.Role.VETERINAIRE,
    User.Role.REFUGE,
)


def _username_from_email(email):
    local = email.split("@")[0][:140]
    base = "".join(c if c.isalnum() or c in "._" else "_" for c in local) or "user"
    candidate = base
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        suffix += 1
        candidate = f"{base[:120]}_{suffix}"
    return candidate


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=PUBLIC_ROLES)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet e-mail.")
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            username=_username_from_email(validated_data["email"]),
            email=validated_data["email"],
            password=validated_data["password"],
            role=validated_data["role"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            phone=validated_data.get("phone", ""),
        )
        if user.role == User.Role.CITOYEN:
            CitoyenProfile.objects.create(user=user)
        elif user.role == User.Role.BENEVOLE:
            BenevoleProfile.objects.create(user=user)
        elif user.role == User.Role.VETERINAIRE:
            VeterinaireProfile.objects.create(user=user)
        return user


class CitoyenProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CitoyenProfile
        fields = ("address",)


class BenevoleProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BenevoleProfile
        fields = ("latitude", "longitude", "is_available", "max_missions", "bio")


class VeterinaireProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = VeterinaireProfile
        fields = (
            "license_number",
            "address",
            "latitude",
            "longitude",
            "is_available",
            "specialties",
            "radius_km",
        )


class RefugeProfileSerializer(serializers.ModelSerializer):
    accepted_species = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Species.objects.all(),
        required=False,
    )

    class Meta:
        model = Refuge
        fields = (
            "name",
            "address",
            "latitude",
            "longitude",
            "phone",
            "description",
            "capacity",
            "action_radius_km",
            "accepted_species",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            for field in ("name", "latitude", "longitude"):
                self.fields[field].required = False


class UserMeSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone",
            "photo",
            "fcm_token",
            "profile",
        )
        read_only_fields = ("id", "username", "email", "role")

    def validate_photo(self, value):
        if value in (None, ""):
            return value
        extension = os.path.splitext(value.name)[1].lower()
        if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise serializers.ValidationError("Formats acceptés : JPG, PNG, WEBP.")
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("La photo ne doit pas dépasser 5 Mo.")
        return value

    def get_profile(self, user):
        if user.role == User.Role.CITOYEN and hasattr(user, "citoyen_profile"):
            return CitoyenProfileSerializer(user.citoyen_profile).data
        if user.role == User.Role.BENEVOLE and hasattr(user, "benevole_profile"):
            return BenevoleProfileSerializer(user.benevole_profile).data
        if user.role == User.Role.VETERINAIRE and hasattr(user, "veterinaire_profile"):
            return VeterinaireProfileSerializer(user.veterinaire_profile).data
        if user.role == User.Role.REFUGE and hasattr(user, "refuge"):
            return RefugeProfileSerializer(user.refuge).data
        return None

    def update(self, user, validated_data):
        profile_data = self.initial_data.get("profile", serializers.empty)
        user.first_name = validated_data.get("first_name", user.first_name)
        user.last_name = validated_data.get("last_name", user.last_name)
        user.phone = validated_data.get("phone", user.phone)
        user.fcm_token = validated_data.get("fcm_token", user.fcm_token)
        update_fields = ["first_name", "last_name", "phone", "fcm_token"]
        if validated_data.get("photo"):
            user.photo = validated_data["photo"]
            update_fields.append("photo")
        user.save(update_fields=update_fields)

        if profile_data is serializers.empty:
            return user
        if profile_data is None:
            raise serializers.ValidationError({"profile": "Le profil ne peut pas être vide."})

        self._update_profile(user, profile_data)
        return user

    def _update_profile(self, user, profile_data):
        if user.role == User.Role.CITOYEN:
            serializer = CitoyenProfileSerializer(user.citoyen_profile, data=profile_data, partial=True)
        elif user.role == User.Role.BENEVOLE:
            serializer = BenevoleProfileSerializer(user.benevole_profile, data=profile_data, partial=True)
        elif user.role == User.Role.VETERINAIRE:
            serializer = VeterinaireProfileSerializer(
                user.veterinaire_profile, data=profile_data, partial=True
            )
        elif user.role == User.Role.REFUGE:
            refuge = getattr(user, "refuge", None)
            serializer = RefugeProfileSerializer(refuge, data=profile_data, partial=refuge is not None)
            serializer.is_valid(raise_exception=True)
            if refuge is None:
                serializer.save(user=user)
            else:
                serializer.save()
            return
        else:
            raise serializers.ValidationError(
                {"profile": "Ce rôle n'a pas de profil éditable."}
            )

        serializer.is_valid(raise_exception=True)
        serializer.save()


class EmailTokenObtainPairSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        if user is None or not user.check_password(attrs["password"]):
            raise serializers.ValidationError("E-mail ou mot de passe incorrect.")
        if not user.is_active:
            raise serializers.ValidationError("Ce compte est désactivé.")
        update_last_login(None, user)
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
