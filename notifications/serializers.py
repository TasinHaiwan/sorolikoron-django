from rest_framework import serializers

from .models import DevicePlatform


class DeviceTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(choices=DevicePlatform.choices)


class DeviceTokenUnregisterSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
