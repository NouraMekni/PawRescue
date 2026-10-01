from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User, VeterinaireProfile
from .serializers import (
    EmailTokenObtainPairSerializer,
    RegisterSerializer,
    UserMeSerializer,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(request=RegisterSerializer, responses={201: UserMeSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        profile = getattr(user, "veterinaire_profile", None)
        if user.role == User.Role.VETERINAIRE and (
            profile is None
            or profile.verification_status != VeterinaireProfile.VerificationStatus.APPROVED
        ):
            return Response(
                {
                    "user": UserMeSerializer(user).data,
                    "detail": "Votre compte est en attente de vérification par un administrateur.",
                },
                status=status.HTTP_201_CREATED,
            )
        tokens = EmailTokenObtainPairSerializer(
            data={"email": user.email, "password": request.data.get("password", "")}
        )
        tokens.is_valid(raise_exception=True)
        return Response(
            {
                "user": UserMeSerializer(user).data,
                "access": tokens.validated_data["access"],
                "refresh": tokens.validated_data["refresh"],
            },
            status=status.HTTP_201_CREATED,
        )


class EmailTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = EmailTokenObtainPairSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @extend_schema(responses={200: UserMeSerializer})
    def get(self, request):
        return Response(UserMeSerializer(request.user, context={"request": request}).data)

    @extend_schema(request=UserMeSerializer, responses={200: UserMeSerializer})
    def patch(self, request):
        serializer = UserMeSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserMeSerializer(request.user, context={"request": request}).data)
