from django.urls import path

from .views import GoogleLoginView, MeView, RegisterView, RepresentativeApplicationCreateView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("google/", GoogleLoginView.as_view(), name="google-login"),
    path("me/", MeView.as_view(), name="me"),
    path(
        "representative-applications/",
        RepresentativeApplicationCreateView.as_view(),
        name="representative-application",
    ),
]
