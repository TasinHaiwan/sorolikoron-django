from django.conf import settings
from django.db import models


class DevicePlatform(models.TextChoices):
    ANDROID = "android", "Android"
    IOS = "ios", "iOS"


class DeviceToken(models.Model):
    """
    An FCM registration token for one device. `token` is globally unique
    (not unique-per-user) — registering a token already owned by a
    different user reassigns it, which is the correct behavior for a
    shared or reinstalled device.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="device_tokens"
    )
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=10, choices=DevicePlatform.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.platform} token for {self.user}"
