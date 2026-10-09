from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import  IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsRefuge, IsVeterinaire

from .models import Animal

from .serializers import (
    AnimalListSerializer,
    AnimalDetailSerializer,
    AnimalCreateSerializer,
    AnimalUpdateSerializer,
    AnimalPhotoSerializer,
    MedicalRecordSerializer,
    MedicalEntrySerializer,
)

from .services import (
    animal_queryset,
    adoptable_animals_queryset,
    create_animal,
    update_animal,
    delete_animal,
    set_animal_adoptable,
    remove_animal_from_adoption,
    add_animal_photo,
    create_medical_record,
    add_medical_entry,
)


class AnimalListCreateView(APIView):
    """
    GET:
        Return all animals.

    POST:
        Any authenticated role can create an animal.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):

        queryset = animal_queryset()

        serializer = AnimalListSerializer(
            queryset,
            many=True,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def post(self, request):

        serializer = AnimalCreateSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        animal = create_animal(
            creator=request.user,
            validated_data=serializer.validated_data,
        )

        animal = animal_queryset().get(
            pk=animal.pk
        )

        response_serializer = AnimalDetailSerializer(
            animal,
            context={
                "request": request,
            },
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class AdoptableAnimalListView(APIView):
    """
    GET:
        Return animals currently available
        for adoption.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):

        queryset = adoptable_animals_queryset()

        serializer = AnimalListSerializer(
            queryset,
            many=True,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class AnimalDetailView(APIView):
    """
    GET:
        Any authenticated user can view an animal.

    PUT/PATCH:
        Only refuges can update an animal.

    DELETE:
        Only refuges can delete an animal.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]

        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [
                IsAuthenticated(),
                IsRefuge(),
            ]

        return [IsAuthenticated()]

    def get_object(self, pk):
        return get_object_or_404(
            animal_queryset(),
            pk=pk,
        )

    def get(self, request, pk):
        animal = self.get_object(pk)

        serializer = AnimalDetailSerializer(
            animal,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def put(self, request, pk):
        animal = self.get_object(pk)

        serializer = AnimalUpdateSerializer(
            animal,
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(raise_exception=True)

        animal = update_animal(
            animal=animal,
            validated_data=serializer.validated_data,
        )

        animal = animal_queryset().get(
            pk=animal.pk
        )

        response_serializer = AnimalDetailSerializer(
            animal,
            context={
                "request": request,
            },
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, pk):
        animal = self.get_object(pk)

        serializer = AnimalUpdateSerializer(
            animal,
            data=request.data,
            partial=True,
            context={
                "request": request,
            },
        )

        serializer.is_valid(raise_exception=True)

        animal = update_animal(
            animal=animal,
            validated_data=serializer.validated_data,
        )

        animal = animal_queryset().get(
            pk=animal.pk
        )

        response_serializer = AnimalDetailSerializer(
            animal,
            context={
                "request": request,
            },
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        animal = self.get_object(pk)

        delete_animal(
            animal=animal,
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )

class AnimalMakeAdoptableView(APIView):
    """
    POST:
        Make an animal available for adoption.
        only refuges can make an animal adoptable.
    """

    permission_classes = [
       IsAuthenticated,
       IsRefuge,
    ]

    def post(self, request, pk):

        animal = get_object_or_404(
            Animal,
            pk=pk,
        )

        animal = set_animal_adoptable(
            animal=animal,
        )

        animal = animal_queryset().get(
            pk=animal.pk
        )

        serializer = AnimalDetailSerializer(
            animal,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class AnimalRemoveFromAdoptionView(APIView):
    """
    POST:
        Remove an animal from adoption availability.

    """

    permission_classes = [
        IsAuthenticated,
        IsRefuge,
    ]

    def post(self, request, pk):

        animal = get_object_or_404(
            Animal,
            pk=pk,
        )

        animal = remove_animal_from_adoption(
            animal=animal,
        )

        animal = animal_queryset().get(
            pk=animal.pk
        )

        serializer = AnimalDetailSerializer(
            animal,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class AnimalPhotoCreateView(APIView):
    """
    POST:
        Add a photo to an animal.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request, pk):

        animal = get_object_or_404(
            Animal,
            pk=pk,
        )

        image = request.FILES.get("image")

        if image is None:
            return Response(
                {
                    "detail": "Une image est obligatoire."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_primary = request.data.get(
            "is_primary",
            False,
        )

        if isinstance(is_primary, str):
            is_primary = (
                is_primary.lower()
                in ["true", "1", "yes"]
            )

        order = request.data.get(
            "order",
            0,
        )

        photo = add_animal_photo(
            animal=animal,
            image=image,
            is_primary=is_primary,
            order=order,
        )

        serializer = AnimalPhotoSerializer(
            photo,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class AnimalMedicalRecordCreateView(APIView):
    """
    POST:
        Create a medical record for an animal.
    """

    permission_classes = [
        IsAuthenticated,
        IsRefuge,
        IsVeterinaire,
    ]

    def post(self, request, pk):

        animal = get_object_or_404(
            Animal,
            pk=pk,
        )

        record = create_medical_record(
            animal=animal,
            allergies=request.data.get(
                "allergies",
                "",
            ),
            shelter_notes=request.data.get(
                "shelter_notes",
                "",
            ),
            next_appointment=request.data.get(
                "next_appointment",
            ),
        )

        serializer = MedicalRecordSerializer(
            record,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class AnimalMedicalRecordDetailView(APIView):
    """
    GET:
        View the medical record of an animal.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, pk):

        animal = get_object_or_404(
            Animal,
            pk=pk,
        )

        record = get_object_or_404(
            animal.medical_record,
        )

        serializer = MedicalRecordSerializer(
            record,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class MedicalEntryCreateView(APIView):
    """
    POST:
        Add a medical entry.
    """

    permission_classes = [
        IsAuthenticated,
        IsRefuge,
        IsVeterinaire,
    ]

    def post(self, request, pk):

        animal = get_object_or_404(
            Animal,
            pk=pk,
        )

        record = get_object_or_404(
            animal.medical_record,
        )

        serializer = MedicalEntrySerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True
        )

        entry = add_medical_entry(
            medical_record=record,
            performed_by=request.user,
            validated_data=serializer.validated_data,
        )

        response_serializer = MedicalEntrySerializer(
            entry,
            context={
                "request": request,
            },
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )