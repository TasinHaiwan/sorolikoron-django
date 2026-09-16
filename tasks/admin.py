from django.contrib import admin
from .models import Service, ServiceRequest, TaskDismissal


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "color_hex", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("title",)
    ordering = ("order",)


class TaskDismissalInline(admin.TabularInline):
    model = TaskDismissal
    extra = 0
    readonly_fields = ("representative", "reason", "note", "dismissed_at")
    can_delete = False


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "service_title", "requested_by", "status", "assigned_representative", "created_at")
    list_editable = ("assigned_representative",)
    list_filter = ("status",)  # filter to "Dismissed" = instant visibility, satisfies req 2
    search_fields = ("service_title", "requested_by__name", "requested_by__phone", "location", "details")
    autocomplete_fields = ("assigned_representative", "requested_by")
    ordering = ("status", "-created_at")  # dismissed/pending surface near the top by default
    inlines = [TaskDismissalInline]  # full dismissal history per task, satisfies req 3