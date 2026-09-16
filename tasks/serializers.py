from rest_framework import serializers
from .models import Service, ServiceRequest


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "title", "color_hex", "order"]


class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = [
            "id",
            "service_title",
            "is_custom",
            "details",
            "contact_number",
            "preferred_date",
            "location",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]