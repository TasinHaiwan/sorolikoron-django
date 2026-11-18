from django.contrib import admin
from django.utils.text import Truncator

from .models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("created_at", "sender", "category", "source", "preview", "is_read")
    list_display_links = ("created_at", "preview")
    list_filter = ("is_read", "category", "source", "created_at")
    search_fields = ("message", "user__email", "user__customer__name", "user__representative__name")
    list_select_related = ("user",)
    date_hierarchy = "created_at"
    # Everything except `is_read` is what the user sent, so it stays read-only.
    fields = ("user", "category", "source", "created_at", "message", "is_read")
    readonly_fields = ("user", "category", "source", "created_at", "message")
    actions = ("mark_read", "mark_unread")

    def has_add_permission(self, request):
        return False  # feedback only comes from the apps and the website

    @admin.display(description="Sender", ordering="user__email")
    def sender(self, obj):
        return obj.user.email if obj.user else "(deleted user)"

    @admin.display(description="Message")
    def preview(self, obj):
        return Truncator(obj.message).chars(80)

    @admin.action(description="Mark selected feedback as read")
    def mark_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description="Mark selected feedback as unread")
    def mark_unread(self, request, queryset):
        queryset.update(is_read=False)
