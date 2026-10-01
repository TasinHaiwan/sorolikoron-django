import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .google_auth import verify_google_id_token
from .models import Customer, PasswordResetCode
from .serializers import (
    PasswordResetConfirmSerializer, PasswordResetRequestSerializer, RegisterSerializer,
    RepresentativeApplicationSerializer, RepresentativeSkillSerializer,
)

PASSWORD_RESET_CODE_TTL = timedelta(minutes=15)

# Generic responses that don't reveal whether an email/code is valid.
_RESET_REQUESTED_RESPONSE = Response(
    {"detail": "If an account exists for this email, a reset code has been sent."},
    status=status.HTTP_200_OK,
)
_RESET_INVALID_RESPONSE = Response(
    {"detail": "That code is invalid or has expired."}, status=status.HTTP_400_BAD_REQUEST,
)


def _email_from_request(request):
    email = request.data.get("email")
    return email.strip().lower() if isinstance(email, str) else ""


class PasswordResetRequestThrottle(SimpleRateThrottle):
    """Keyed on the requested email (falling back to IP) so one address
    can't be hammered with reset emails regardless of source IP, while a
    single IP can't fan out requests across many addresses either."""

    scope = "password_reset_request"

    def get_cache_key(self, request, view):
        ident = _email_from_request(request) or self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class PasswordResetConfirmThrottle(SimpleRateThrottle):
    scope = "password_reset_confirm"

    def get_cache_key(self, request, view):
        ident = _email_from_request(request) or self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


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


class PasswordResetRequestView(APIView):
    """Starts a password reset: emails a 6-digit code if the address has
    an account. Always responds the same way either way, so the response
    never reveals whether the email exists."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRequestThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(username__iexact=email).first()
        if user is not None:
            code = f"{secrets.randbelow(1_000_000):06d}"
            # A fresh request supersedes any still-pending code for this user.
            PasswordResetCode.objects.filter(user=user, consumed_at__isnull=True).delete()
            PasswordResetCode.objects.create(
                user=user,
                code_hash=make_password(code),
                expires_at=timezone.now() + PASSWORD_RESET_CODE_TTL,
            )
            send_mail(
                subject="Your Shorolikoron password reset code",
                message=(
                    f"Your password reset code is {code}.\n\n"
                    "It expires in 15 minutes. If you didn't request this, you can ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )

        return _RESET_REQUESTED_RESPONSE


class PasswordResetConfirmView(APIView):
    """Verifies the emailed code and sets the new password. Also never
    reveals whether the email exists — an unknown email and a wrong/expired
    code both get the same generic error."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetConfirmThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]
        new_password = serializer.validated_data["new_password"]

        user = User.objects.filter(username__iexact=email).first()
        if user is None:
            return _RESET_INVALID_RESPONSE

        reset_code = PasswordResetCode.objects.filter(user=user, consumed_at__isnull=True).first()
        if reset_code is None or not reset_code.is_usable:
            return _RESET_INVALID_RESPONSE

        if not check_password(code, reset_code.code_hash):
            reset_code.attempts += 1
            reset_code.save(update_fields=["attempts"])
            return _RESET_INVALID_RESPONSE

        user.set_password(new_password)
        user.save(update_fields=["password"])
        reset_code.consumed_at = timezone.now()
        reset_code.save(update_fields=["consumed_at"])

        return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)


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
