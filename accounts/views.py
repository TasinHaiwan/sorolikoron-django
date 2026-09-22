from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .google_auth import verify_google_id_token
from .models import Customer
from .serializers import (
    RegisterSerializer, RepresentativeApplicationSerializer, RepresentativeSkillSerializer,
)


def _tokens_for(user):
    refresh = RefreshToken.for_user(user)
    customer = getattr(user, "customer", None)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "email": user.email,
            "name": customer.name if customer else "",
        },
    }


class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(_tokens_for(user), status=status.HTTP_201_CREATED)


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        id_token = request.data.get("id_token")
        if not id_token:
            return Response({"id_token": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            idinfo = verify_google_id_token(id_token)
        except ValueError:
            return Response({"detail": "Invalid Google token."}, status=status.HTTP_401_UNAUTHORIZED)

        email = idinfo.get("email")
        if not email:
            return Response({"detail": "Google account has no email."}, status=status.HTTP_400_BAD_REQUEST)
        name = idinfo.get("name", "")

        user, created = User.objects.get_or_create(username=email, defaults={"email": email})
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        if not hasattr(user, "customer"):
            Customer.objects.create(user=user, name=name)

        return Response(_tokens_for(user), status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, "customer", None) or getattr(request.user, "representative", None)
        skills = RepresentativeSkillSerializer(profile.skills.all(), many=True).data if hasattr(profile, "skills") else []
        return Response({
            "id": request.user.id,
            "email": request.user.email,
            "name": profile.name if profile else "",
            "phone": profile.phone if profile else "",
            "role": "representative" if hasattr(request.user, "representative") else "customer",
            "is_available": getattr(profile, "is_available", None),
            "coverage_area": getattr(profile, "coverage_area", None),
            "skills": skills,
        })


class RepresentativeApplicationCreateView(CreateAPIView):
    serializer_class = RepresentativeApplicationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        return Response(
            {"id": application.id, "status": application.status},
            status=status.HTTP_201_CREATED,
        )
