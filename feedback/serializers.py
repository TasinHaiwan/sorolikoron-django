from rest_framework import serializers

from .models import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ("id", "category", "message", "source", "created_at")
        read_only_fields = ("id", "created_at")
