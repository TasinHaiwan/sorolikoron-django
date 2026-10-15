from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DeviceToken
from .serializers import DeviceTokenSerializer, DeviceTokenUnregisterSerializer


class DeviceTokenRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        DeviceToken.objects.update_or_create(
            token=serializer.validated_data["token"],
            defaults={
                "user": request.user,
                "platform": serializer.validated_data["platform"],
            },
        )
        return Response(status=http_status.HTTP_200_OK)


class DeviceTokenUnregisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenUnregisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        DeviceToken.objects.filter(
            user=request.user, token=serializer.validated_data["token"]
        ).delete()
        return Response(status=http_status.HTTP_200_OK)
