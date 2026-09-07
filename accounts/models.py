from django.db import models

class Customer(models.Model):
    # Filled in by the API the first time a Firebase-authenticated
    # customer hits the backend (upsert by firebase_uid). Admin can
    # also add these manually for testing.
    is_authenticated = True  # lets DRF's IsAuthenticated permission treat this as a logged-in user
    firebase_uid = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or self.phone or self.firebase_uid

class Representative(models.Model):
    is_authenticated = True
    firebase_uid = models.CharField(max_length=128, unique=True, null=True, blank=True)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_available = models.BooleanField(default=False)
    available_since = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.id} — {self.name}"