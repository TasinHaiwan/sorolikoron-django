from django.conf import settings
from django.db import models


class FeedbackCategory(models.TextChoices):
    SUGGESTION = "suggestion", "Suggestion"
    PROBLEM = "problem", "Problem"
    PRAISE = "praise", "Praise"
    OTHER = "other", "Other"


class FeedbackSource(models.TextChoices):
    WEBSITE = "website", "Website"
    CUSTOMER_APP = "customer_app", "Customer app"
    REPRESENTATIVE_APP = "representative_app", "Representative app"


class Feedback(models.Model):
    """A message a signed-in user sends from "Write a Feedback". Staff read
    it in the admin and tick `is_read` once handled. There is no reply path;
    to follow up, staff contact the sender directly."""

    MESSAGE_MAX_LENGTH = 2000

    # SET_NULL so deleting an account doesn't delete what they told us.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="feedback",
    )
    category = models.CharField(max_length=20, choices=FeedbackCategory.choices)
    message = models.TextField(max_length=MESSAGE_MAX_LENGTH)
    source = models.CharField(
        max_length=20, choices=FeedbackSource.choices, default=FeedbackSource.WEBSITE,
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "feedback"

    def __str__(self):
        sender = self.user.email if self.user else "deleted user"
        return f"{self.get_category_display()} from {sender} ({self.created_at:%Y-%m-%d})"
