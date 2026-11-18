from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle

from .serializers import FeedbackSerializer


class FeedbackCreateView(CreateAPIView):
    """Any signed-in user (customer or representative) can send feedback."""

    permission_classes = [IsAuthenticated]
    serializer_class = FeedbackSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "feedback"

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
