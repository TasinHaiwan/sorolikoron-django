from django.templatetags.static import static
from rest_framework import serializers
from .models import Service, ServiceRequest


class ServiceSerializer(serializers.ModelSerializer):
    icon_url = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ["id", "title", "description", "color_hex", "icon_url", "order"]

    def get_icon_url(self, obj):
        if not obj.icon_slug:
            return None
        path = static(f"service_icons/{obj.icon_slug}.svg")
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path


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


class RepTaskSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="requested_by.name", read_only=True)

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
            "dismiss_reason",
            "dismiss_note",
            "customer_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields