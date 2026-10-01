from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status as http_status
from .models import HomeBanner, Service, ServiceRequest, TaskStatus, TaskDismissal
from .permissions import IsCustomer, IsRepresentative
from .serializers import (
    HomeBannerSerializer, RepTaskSerializer, ServiceRequestCreateSerializer, ServiceSerializer,
)

class ServiceListView(ListAPIView):
    serializer_class = ServiceSerializer
    queryset = Service.objects.filter(is_active=True)


class HomeBannerListView(ListAPIView):
    """All active banners, in admin-defined order — no page size cap,
    the customer app's carousel renders every one it gets back."""
    serializer_class = HomeBannerSerializer
    queryset = HomeBanner.objects.filter(is_active=True)


ONGOING_STATUSES = [TaskStatus.PENDING, TaskStatus.CONFIRMED, TaskStatus.IN_PROGRESS]


class ServiceRequestListCreateView(ListCreateAPIView):
    """
    Supports optional filtering via query params, used by the customer
    app's home screen (ongoing only) and Activity tab (date range):
    - `ongoing=true` — only pending/confirmed/in_progress requests.
    - `date_from`, `date_to` (YYYY-MM-DD, inclusive) — filtered against
      `created_at` in the server's timezone (UTC).
    With no params, behaves as before: the customer's full history.
    """
    serializer_class = ServiceRequestCreateSerializer
    permission_classes = [IsAuthenticated, IsCustomer]

    def get_queryset(self):
        queryset = ServiceRequest.objects.filter(requested_by=self.request.user.customer)

        if self.request.query_params.get("ongoing") == "true":
            queryset = queryset.filter(status__in=ONGOING_STATUSES)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user.customer)


class RepAssignedTasksView(ListAPIView):
    permission_classes = [IsAuthenticated, IsRepresentative]
    serializer_class = RepTaskSerializer

    def get_queryset(self):
        return ServiceRequest.objects.filter(
            assigned_representative=self.request.user.representative,
            status__in=[
                TaskStatus.PENDING,
                TaskStatus.CONFIRMED,
                TaskStatus.IN_PROGRESS,
                TaskStatus.COMPLETED,
            ],
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
        task.confirmed_at = timezone.now()
        task.save(update_fields=["status", "confirmed_at", "updated_at"])
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
        task.confirmed_at = None
        task.save(update_fields=["status", "confirmed_at", "updated_at"])
        return Response({"status": task.status})


class RepStartTaskView(APIView):
    permission_classes = [IsAuthenticated, IsRepresentative]

    def post(self, request, pk):
        task = ServiceRequest.objects.filter(pk=pk, assigned_representative=request.user.representative).first()
        if task is None:
            return Response({"detail": "Task not found"}, status=http_status.HTTP_404_NOT_FOUND)
        if task.status != TaskStatus.CONFIRMED:
            return Response({"detail": "Only confirmed tasks can be started"}, status=http_status.HTTP_400_BAD_REQUEST)
        task.status = TaskStatus.IN_PROGRESS
        task.save(update_fields=["status", "updated_at"])
        return Response({"status": task.status})


class RepCompleteTaskView(APIView):
    permission_classes = [IsAuthenticated, IsRepresentative]

    def post(self, request, pk):
        task = ServiceRequest.objects.filter(pk=pk, assigned_representative=request.user.representative).first()
        if task is None:
            return Response({"detail": "Task not found"}, status=http_status.HTTP_404_NOT_FOUND)
        if task.status != TaskStatus.IN_PROGRESS:
            return Response({"detail": "Only in-progress tasks can be completed"}, status=http_status.HTTP_400_BAD_REQUEST)
        task.status = TaskStatus.COMPLETED
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


class RepReportView(APIView):
    """
    Task counts by status, completion rate, and average response time for
    the authenticated representative, over an inclusive `date_from`/
    `date_to` (YYYY-MM-DD) range — both required. Counts are scoped to
    tasks *created* in that range.

    Dismissing a task clears `assigned_representative` (see
    `RepDismissTaskView`), so the dismissed count is read from
    `TaskDismissal` instead, joined back to the request's `created_at` for
    the same range semantics as the other statuses.
    """
    permission_classes = [IsAuthenticated, IsRepresentative]

    def get(self, request):
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        if not date_from or not date_to:
            return Response(
                {"detail": "date_from and date_to are required."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        rep = request.user.representative
        assigned_qs = ServiceRequest.objects.filter(
            assigned_representative=rep,
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
        )

        counts = {status: 0 for status in TaskStatus.values}
        for row in assigned_qs.values("status").annotate(count=Count("id")):
            counts[row["status"]] = row["count"]

        counts[TaskStatus.DISMISSED] = TaskDismissal.objects.filter(
            representative=rep,
            service_request__created_at__date__gte=date_from,
            service_request__created_at__date__lte=date_to,
        ).count()

        completed_count = counts[TaskStatus.COMPLETED]
        resolved_count = completed_count + counts[TaskStatus.DISMISSED]
        completion_rate = completed_count / resolved_count if resolved_count else 0.0

        response_times = [
            (row["confirmed_at"] - row["created_at"]).total_seconds()
            for row in assigned_qs.filter(confirmed_at__isnull=False).values(
                "created_at", "confirmed_at"
            )
        ]
        average_response_time_seconds = (
            int(sum(response_times) / len(response_times)) if response_times else None
        )

        return Response({
            "tasks": counts,
            "completion_rate": round(completion_rate, 4),
            "average_response_time_seconds": average_response_time_seconds,
        })