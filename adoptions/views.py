from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsCitoyen, IsRefugeOrAdmin

from .models import AdoptionRequest
from .serializers import (
    AdoptionRequestSerializer,
    AdoptionRequestCreateSerializer,
    AdoptionReviewSerializer,
)
from .services import (
    adoption_queryset,
    approve_adoption_request,
    cancel_adoption_request,
    create_adoption_request,
    reject_adoption_request,
    visible_adoptions,
)


class AdoptionListCreateView(APIView):
    """
    GET:
        List adoption requests visible to the current user.

    POST:
        Create a new adoption request.
        Only citizens can create requests.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = visible_adoptions(request.user)

        queryset = adoption_queryset().filter(
            pk__in=queryset.values("pk")
        )

        serializer = AdoptionRequestSerializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        if request.user.role != User.Role.CITOYEN:
            return Response(
                {
                    "detail": (
                        "Seuls les citoyens peuvent "
                        "envoyer une demande d'adoption."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AdoptionRequestCreateSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(raise_exception=True)

        adoption = create_adoption_request(
            applicant=request.user,
            animal=serializer.validated_data["animal"],
            message=serializer.validated_data.get(
                "message",
                "",
            ),
        )

        adoption = (
            adoption_queryset()
            .get(pk=adoption.pk)
        )

        response_serializer = AdoptionRequestSerializer(
            adoption
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class AdoptionDetailView(APIView):
    """
    GET:
        View one adoption request.

    Access:
        - citizen: own request
        - refuge: requests belonging to its refuge
        - admin: all
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        queryset = visible_adoptions(request.user)

        return get_object_or_404(
            adoption_queryset().filter(
                pk__in=queryset.values("pk")
            ),
            pk=pk,
        )

    def get(self, request, pk):
        adoption = self.get_object(
            request,
            pk,
        )

        serializer = AdoptionRequestSerializer(
            adoption
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class AdoptionCancelView(APIView):
    """
    POST:
        Cancel a pending adoption request.

    Only the citizen who created the request
    can cancel it.
    """

    permission_classes = [
        IsAuthenticated,
        IsCitoyen,
    ]

    def post(self, request, pk):
        adoption = get_object_or_404(
            AdoptionRequest,
            pk=pk,
        )

        adoption = cancel_adoption_request(
            adoption_request=adoption,
            applicant=request.user,
        )

        adoption = (
            adoption_queryset()
            .get(pk=adoption.pk)
        )

        serializer = AdoptionRequestSerializer(
            adoption
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class AdoptionApproveView(APIView):
    """
    POST:
        Approve an adoption request.

    Only refuge/admin users can approve.
    """

    permission_classes = [
        IsAuthenticated,
        IsRefugeOrAdmin,
    ]

    def post(self, request, pk):
        adoption = get_object_or_404(
            AdoptionRequest,
            pk=pk,
        )

        serializer = AdoptionReviewSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        adoption = approve_adoption_request(
            adoption_request=adoption,
            reviewer=request.user,
            review_note=serializer.validated_data.get(
                "review_note",
                "",
            ),
        )

        adoption = (
            adoption_queryset()
            .get(pk=adoption.pk)
        )

        response_serializer = AdoptionRequestSerializer(
            adoption
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )


class AdoptionRejectView(APIView):
    """
    POST:
        Reject an adoption request.

    Only refuge/admin users can reject.
    """

    permission_classes = [
        IsAuthenticated,
        IsRefugeOrAdmin,
    ]

    def post(self, request, pk):
        adoption = get_object_or_404(
            AdoptionRequest,
            pk=pk,
        )

        serializer = AdoptionReviewSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        adoption = reject_adoption_request(
            adoption_request=adoption,
            reviewer=request.user,
            review_note=serializer.validated_data.get(
                "review_note",
                "",
            ),
        )

        adoption = (
            adoption_queryset()
            .get(pk=adoption.pk)
        )

        response_serializer = AdoptionRequestSerializer(
            adoption
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )