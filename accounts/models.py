from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class Customer(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="customer",
    )
    name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
            return self.name or self.phone or self.user.email


class Representative(models.Model):
    user = models.OneToOneField(
         User,
         on_delete=models.CASCADE,
         related_name="representative",
    )
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    is_available = models.BooleanField(default=False)
    availability_updated_at = models.DateTimeField(null=True, blank=True)
    coverage_area = models.CharField(
        max_length=255, blank=True,
        help_text="The area/routes this representative serves, e.g. 'Dhaka campus routes'.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.id} — {self.name}"


class SkillLevel(models.TextChoices):
    BEGINNER = "beginner", "Beginner"
    INTERMEDIATE = "intermediate", "Intermediate"
    ADVANCED = "advanced", "Advanced"


class RepresentativeSkill(models.Model):
    """A skill assigned to a representative by an admin — shown read-only
    on the rep's own profile."""
    representative = models.ForeignKey(Representative, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=SkillLevel.choices, default=SkillLevel.BEGINNER)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.representative.name} — {self.name} ({self.level})"


class RepresentativeApplicationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class RepresentativeApplication(models.Model):
    """A "request to become a representative" submitted from the rep app.
    Approving one provisions a User + Representative using the submitted
    credentials, so the applicant can then sign in normally; rejecting
    one just records the decision. No account exists until approved.
    """
    name = models.CharField(max_length=150)
    email = models.EmailField()
    password_hash = models.CharField(max_length=128)
    status = models.CharField(
        max_length=10, choices=RepresentativeApplicationStatus.choices,
        default=RepresentativeApplicationStatus.PENDING,
    )
    decision_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} <{self.email}> — {self.status}"


class PasswordResetCode(models.Model):
    """A one-time 6-digit code emailed to a user to authorize a password
    reset. Only the hash is stored; the plaintext code only ever exists
    in the outgoing email. One row per request — a new request doesn't
    reuse or extend an existing row, it supersedes it (see the view)."""

    MAX_ATTEMPTS = 5

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_codes")
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"reset code for {self.user.email} (created {self.created_at:%Y-%m-%d %H:%M})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_usable(self):
        return self.consumed_at is None and not self.is_expired and self.attempts < self.MAX_ATTEMPTS