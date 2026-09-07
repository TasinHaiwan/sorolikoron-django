from django.contrib import admin
from .models import Customer, Representative

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "email", "created_at")
    search_fields = ("name", "phone", "email", "firebase_uid")

@admin.register(Representative)
class RepresentativeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "is_available")
    list_editable = ("is_available",)
    list_filter = ("is_available",)
    search_fields = ("name", "phone")