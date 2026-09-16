from django.db import models
from accounts.models import Customer, Representative
from django.db.models.signals import pre_save
from django.dispatch import receiver

class ServiceCategory(models.TextChoices):
    ELECTRICAL = "electrical", "Electrical"
    PLUMBING = "plumbing", "Plumbing"
    CLEANING = "cleaning", "Cleaning"
    OTHER = "other", "Other"

class TaskStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    IN_PROGRESS = "in_progress", "In Progress"
    DISMISSED = "dismissed", "Dismissed"

class DismissReason(models.TextChoices):
    CUSTOMER_CANCELLED = "customer_cancelled", "Customer Cancelled"
    OUT_OF_AREA = "out_of_area", "Out of Area"
    DUPLICATE = "duplicate", "Duplicate"
    OTHER = "other", "Other"

class Service(models.Model):
    title = models.CharField(max_length=150, unique=True)
    color_hex = models.CharField(max_length=9, default="#2352CC")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title

class ServiceRequest(models.Model):
    requested_by = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="requests"
    )
    service_title = models.CharField(max_length=255)
    is_custom = models.BooleanField(default=False)
    details = models.TextField(blank=True)
    contact_number = models.CharField(max_length=20)
    preferred_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)

    status = models.CharField(
        max_length=30, choices=TaskStatus.choices, default=TaskStatus.PENDING
    )
    assigned_representative = models.ForeignKey(
        Representative,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_requests",
    )

    dismiss_reason = models.CharField(max_length=30, choices=DismissReason.choices, blank=True)
    dismiss_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"#{self.id} {self.service_title} — {self.requested_by}"

class TaskDismissal(models.Model):
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="dismissals")
    representative = models.ForeignKey(Representative, on_delete=models.CASCADE, related_name="dismissals")
    reason = models.CharField(max_length=30, choices=DismissReason.choices)
    note = models.TextField(blank=True)
    dismissed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.representative} dismissed #{self.service_request_id}"

@receiver(pre_save, sender=ServiceRequest)
def reset_status_on_reassignment(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        previous = ServiceRequest.objects.get(pk=instance.pk)
    except ServiceRequest.DoesNotExist:
        return
    # Whenever admin assigns/replaces to a *new* rep, treat it as a fresh assignment
    if (instance.assigned_representative_id != previous.assigned_representative_id
            and instance.assigned_representative_id is not None):
        instance.status = TaskStatus.PENDING