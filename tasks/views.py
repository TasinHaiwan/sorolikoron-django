from django.shortcuts import render
from django.utils import timezone
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status as http_status
from .models import Service, ServiceRequest, TaskStatus, TaskDismissal
from .permissions import IsCustomer, IsRepresentative
from .serializers import RepTaskSerializer, ServiceRequestCreateSerializer, ServiceSerializer

class ServiceListView(ListAPIView):
    serializer_class = ServiceSerializer
    queryset = Service.objects.filter(is_active=True)


class ServiceRequestCreateView(CreateAPIView):
    serializer_class = ServiceRequestCreateSerializer
    permission_classes = [IsAuthenticated, IsCustomer]

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user.customer)


class RepAssignedTasksView(ListAPIView):
    permission_classes = [IsAuthenticated, IsRepresentative]
    serializer_class = RepTaskSerializer

    def get_queryset(self):
        return ServiceRequest.objects.filter(
            assigned_representative=self.request.user.representative,
            status__in=[TaskStatus.PENDING, TaskStatus.CONFIRMED,],
        ).order_by("-created_at")


class RepAvailabilityView(APIView):
    permission_classes = [IsAuthenticated, IsRepresentative]

    def post(self, request):
        is_available = request.data.get("is_available")
        if not isinstance(is_available, bool):
            return Response(
                {"is_available": ["This field is required and must be true or false."]},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        rep = request.user.representative
        rep.is_available = is_available
        rep.availability_updated_at = timezone.now()
        rep.save(update_fields=["is_available", "availability_updated_at"])
        return Response({"is_available": rep.is_available})


class RepConfirmTaskView(APIView):
    permission_classes = [IsAuthenticated, IsRepresentative]

    def post(self, request, pk):
        task = ServiceRequest.objects.filter(pk=pk, assigned_representative=request.user.representative).first()
        if task is None:
            return Response({"detail": "Task not found"}, status=http_status.HTTP_404_NOT_FOUND)
        if task.status != TaskStatus.PENDING:
            return Response({"detail": "Only pending tasks can be confirmed"}, status=http_status.HTTP_400_BAD_REQUEST)
        task.status = TaskStatus.CONFIRMED
        task.save(update_fields=["status", "updated_at"])
        return Response({"status": task.status})


class RepUndoConfirmTaskView(APIView):
    permission_classes = [IsAuthenticated, IsRepresentative]

    def post(self, request, pk):
        task = ServiceRequest.objects.filter(pk=pk, assigned_representative=request.user.representative).first()
        if task is None:
            return Response({"detail": "Task not found"}, status=http_status.HTTP_404_NOT_FOUND)
        if task.status != TaskStatus.CONFIRMED:
            return Response({"detail": "Only confirmed tasks can be undone"}, status=http_status.HTTP_400_BAD_REQUEST)
        task.status = TaskStatus.PENDING
        task.save(update_fields=["status", "updated_at"])
        return Response({"status": task.status})


class RepDismissTaskView(APIView):
    permission_classes = [IsAuthenticated, IsRepresentative]

    def post(self, request, pk):
        task = ServiceRequest.objects.filter(pk=pk, assigned_representative=request.user.representative).first()
        if task is None:
            return Response({"detail": "Task not found"}, status=http_status.HTTP_404_NOT_FOUND)
        if task.status not in [TaskStatus.PENDING, TaskStatus.CONFIRMED]:
            return Response({"detail": "This task cannot be dismissed"}, status=http_status.HTTP_400_BAD_REQUEST)

        reason = request.data.get("reason")
        note = request.data.get("note", "")
        if not reason:
            return Response({"detail": "reason is required"}, status=http_status.HTTP_400_BAD_REQUEST)

        TaskDismissal.objects.create(
            service_request=task, representative=request.user.representative, reason=reason, note=note,
        )
        task.dismiss_reason = reason
        task.dismiss_note = note
        task.status = TaskStatus.DISMISSED
        task.assigned_representative = None  # frees it up for reassignment
        task.save()
        return Response({"status": task.status})