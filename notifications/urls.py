from django.urls import path

from .views import DeviceTokenRegisterView, DeviceTokenUnregisterView

urlpatterns = [
    path("device-tokens/", DeviceTokenRegisterView.as_view()),
    path("device-tokens/unregister/", DeviceTokenUnregisterView.as_view()),
]
