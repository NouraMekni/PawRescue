from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsRefugeOrAdmin
from .serializers import AdoptionRequestSerializer, AdoptionRequestCreateSerializer, AdoptionReviewSerializer
from .services import (
    APPLICANT_ROLES, adoption_queryset, visible_adoptions, create_adoption_request,
    cancel_adoption_request, approve_adoption_request, reject_adoption_request,
)


def visible_request(user, pk):
    return get_object_or_404(adoption_queryset().filter(pk__in=visible_adoptions(user).values("pk")), pk=pk)


class AdoptionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = adoption_queryset().filter(pk__in=visible_adoptions(request.user).values("pk"))
        animal = request.query_params.get("animal")
        if animal is not None:
            try:
                animal = int(animal)
                if animal <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise ValidationError({"animal": "Identifiant animal invalide."})
            queryset = queryset.filter(animal_id=animal)
        return Response(AdoptionRequestSerializer(queryset, many=True, context={"request": request}).data)

    def post(self, request):
        if request.user.role not in APPLICANT_ROLES:
            return Response({"detail": "Seuls les citoyens et bénévoles peuvent envoyer une demande d'adoption."}, status=status.HTTP_403_FORBIDDEN)
        serializer = AdoptionRequestCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        adoption = create_adoption_request(applicant=request.user, **serializer.validated_data)
        adoption = adoption_queryset().get(pk=adoption.pk)
        return Response(AdoptionRequestSerializer(adoption, context={"request": request}).data, status=status.HTTP_201_CREATED)


class AdoptionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        return Response(AdoptionRequestSerializer(visible_request(request.user, pk), context={"request": request}).data)


class AdoptionCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        adoption = cancel_adoption_request(adoption_request=visible_request(request.user, pk), applicant=request.user)
        return Response(AdoptionRequestSerializer(adoption_queryset().get(pk=adoption.pk), context={"request": request}).data)


class AdoptionApproveView(APIView):
    permission_classes = [IsAuthenticated, IsRefugeOrAdmin]

    def post(self, request, pk):
        adoption = visible_request(request.user, pk)
        serializer = AdoptionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        adoption = approve_adoption_request(adoption_request=adoption, reviewer=request.user, **serializer.validated_data)
        return Response(AdoptionRequestSerializer(adoption_queryset().get(pk=adoption.pk), context={"request": request}).data)


class AdoptionRejectView(APIView):
    permission_classes = [IsAuthenticated, IsRefugeOrAdmin]

    def post(self, request, pk):
        adoption = visible_request(request.user, pk)
        serializer = AdoptionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        adoption = reject_adoption_request(adoption_request=adoption, reviewer=request.user, **serializer.validated_data)
        return Response(AdoptionRequestSerializer(adoption_queryset().get(pk=adoption.pk), context={"request": request}).data)
