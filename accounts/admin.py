from django.contrib import admin
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    Customer, PasswordResetCode, Representative, RepresentativeApplication,
    RepresentativeApplicationStatus, RepresentativeSkill,
)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "user", "created_at")
    search_fields = ("name", "phone", "user__email", "user__username")


class RepresentativeSkillInline(admin.TabularInline):
    model = RepresentativeSkill
    extra = 1


@admin.register(Representative)
class RepresentativeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "is_available", "coverage_area", "skills_list")
    list_editable = ("is_available", "coverage_area")
    list_filter = ("is_available",)
    search_fields = ("name", "phone", "user__email", "user__username")
    inlines = [RepresentativeSkillInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("skills")

    @admin.display(description="Skills")
    def skills_list(self, obj):
        return ", ".join(skill.name for skill in obj.skills.all()) or "—"


@admin.register(RepresentativeApplication)
class RepresentativeApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "status", "submitted_at", "decided_at")
    list_filter = ("status",)
    search_fields = ("name", "email")
    readonly_fields = ("password_hash", "submitted_at", "decided_at")
    actions = ["approve_applications", "reject_applications"]

    @admin.action(description="Approve selected applications")
    def approve_applications(self, request, queryset):
        approved_count = 0
        for application in queryset.filter(status=RepresentativeApplicationStatus.PENDING):
            if User.objects.filter(username__iexact=application.email).exists():
                continue  # an account already exists for this email — needs manual review

            user = User(username=application.email, email=application.email)
            user.password = application.password_hash
            user.save()
            Representative.objects.create(user=user, name=application.name)

            application.status = RepresentativeApplicationStatus.APPROVED
            application.decided_at = timezone.now()
            application.save(update_fields=["status", "decided_at"])
            approved_count += 1

        self.message_user(request, f"Approved {approved_count} application(s).")

    @admin.action(description="Reject selected applications")
    def reject_applications(self, request, queryset):
        updated = queryset.filter(status=RepresentativeApplicationStatus.PENDING).update(
            status=RepresentativeApplicationStatus.REJECTED, decided_at=timezone.now()
        )
        self.message_user(request, f"Rejected {updated} application(s).")


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    """Read-only — codes are only ever created/consumed by the API."""

    list_display = ("id", "user", "created_at", "expires_at", "attempts", "consumed_at")
    list_filter = ("consumed_at",)
    search_fields = ("user__email", "user__username")
    readonly_fields = [f.name for f in PasswordResetCode._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
