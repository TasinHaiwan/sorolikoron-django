from django.urls import path

from .views import (
    GoogleLoginView, MeView, PasswordResetConfirmView, PasswordResetRequestView, RegisterView,
    RepresentativeApplicationCreateView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("google/", GoogleLoginView.as_view(), name="google-login"),
    path("me/", MeView.as_view(), name="me"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "representative-applications/",
        RepresentativeApplicationCreateView.as_view(),
        name="representative-application",
    ),
]
