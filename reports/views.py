from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsCitoyen

from .models import Report
from .serializers import ReportCreateSerializer, ReportSerializer
from .services import haversine_km

NEARBY_ROLES = (User.Role.CITOYEN, User.Role.BENEVOLE, User.Role.REFUGE)


def visible_reports(user):
    if user.role == User.Role.CITOYEN:
        return Report.objects.filter(reporter=user)
    if user.role == User.Role.REFUGE:
        refuge = getattr(user, "refuge", None)
        if refuge is None:
            return Report.objects.none()
        return Report.objects.filter(assigned_refuge=refuge)
    return None


def report_queryset():
    return Report.objects.select_related(
        "species",
        "assigned_refuge",
        "reporter",
    ).prefetch_related("photos")


class ReportListCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsCitoyen()]
        return [IsAuthenticated()]

    @extend_schema(responses={200: ReportSerializer(many=True)})
    def get(self, request):
        reports = visible_reports(request.user)
        if reports is None:
            return Response(status=status.HTTP_403_FORBIDDEN)
        reports = report_queryset().filter(pk__in=reports.values("pk"))
        return Response(ReportSerializer(reports, many=True, context={"request": request}).data)

    @extend_schema(
        request={"multipart/form-data": ReportCreateSerializer},
        responses={201: ReportSerializer},
    )
    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        report = report_queryset().get(pk=report.pk)
        return Response(
            ReportSerializer(report, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ReportDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ReportSerializer})
    def get(self, request, pk):
        reports = visible_reports(request.user)
        if reports is None:
            return Response(status=status.HTTP_403_FORBIDDEN)
        report = get_object_or_404(report_queryset().filter(pk__in=reports.values("pk")), pk=pk)
        return Response(ReportSerializer(report, context={"request": request}).data)


class ReportNearbyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("latitude", float, required=True),
            OpenApiParameter("longitude", float, required=True),
            OpenApiParameter("radius_km", float, required=False),
            OpenApiParameter("species", int, required=False),
            OpenApiParameter("status", str, required=False),
        ],
        responses={200: ReportSerializer(many=True)},
    )
    def get(self, request):
        if request.user.role not in NEARBY_ROLES:
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            latitude = float(request.query_params["latitude"])
            longitude = float(request.query_params["longitude"])
            radius_km = float(request.query_params.get("radius_km", 20))
        except (KeyError, TypeError, ValueError):
            return Response(
                {"detail": "latitude et longitude sont obligatoires."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reports = report_queryset()
        species = request.query_params.get("species")
        report_status = request.query_params.get("status")
        if species:
            reports = reports.filter(species_id=species)
        if report_status:
            reports = reports.filter(status=report_status)

        nearby = []
        for report in reports:
            distance = haversine_km(latitude, longitude, report.latitude, report.longitude)
            if distance <= radius_km:
                data = ReportSerializer(report, context={"request": request}).data
                data["distance_km"] = round(distance, 2)
                nearby.append((distance, data))
        nearby.sort(key=lambda item: item[0])
        return Response([item[1] for item in nearby])
