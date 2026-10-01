from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from .models import Customer, PasswordResetCode


class PasswordResetRequestTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="jane@example.com", email="jane@example.com", password="old-password",
        )
        Customer.objects.create(user=self.user, name="Jane")

    def test_known_email_creates_code_and_sends_mail(self):
        response = self.client.post("/api/auth/password-reset/", {"email": "jane@example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(PasswordResetCode.objects.filter(user=self.user).count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["jane@example.com"])

    def test_unknown_email_responds_identically_and_sends_no_mail(self):
        known_response = self.client.post("/api/auth/password-reset/", {"email": "jane@example.com"})
        cache.clear()  # isolate from the request-scoped throttle
        unknown_response = self.client.post(
            "/api/auth/password-reset/", {"email": "nobody@example.com"}
        )

        self.assertEqual(known_response.status_code, unknown_response.status_code)
        self.assertEqual(known_response.json(), unknown_response.json())
        self.assertEqual(len(mail.outbox), 1)  # only the known-email request sent anything

    def test_new_request_supersedes_previous_pending_code(self):
        self.client.post("/api/auth/password-reset/", {"email": "jane@example.com"})
        cache.clear()
        self.client.post("/api/auth/password-reset/", {"email": "jane@example.com"})

        self.assertEqual(PasswordResetCode.objects.filter(user=self.user).count(), 1)

    def test_request_is_throttled(self):
        for _ in range(3):
            response = self.client.post("/api/auth/password-reset/", {"email": "jane@example.com"})
            self.assertEqual(response.status_code, 200)

        throttled = self.client.post("/api/auth/password-reset/", {"email": "jane@example.com"})
        self.assertEqual(throttled.status_code, 429)

    def test_invalid_email_is_rejected(self):
        response = self.client.post("/api/auth/password-reset/", {"email": "not-an-email"})
        self.assertEqual(response.status_code, 400)


class PasswordResetConfirmTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="jane@example.com", email="jane@example.com", password="old-password",
        )
        Customer.objects.create(user=self.user, name="Jane")

    def _request_code(self):
        self.client.post("/api/auth/password-reset/", {"email": "jane@example.com"})
        cache.clear()  # isolate the confirm calls from the request endpoint's throttle
        body = mail.outbox[-1].body
        return next(word.strip(".") for word in body.split() if word.strip(".").isdigit() and len(word.strip(".")) == 6)

    def test_valid_code_sets_new_password(self):
        code = self._request_code()

        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"email": "jane@example.com", "code": code, "new_password": "new-password-123"},
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new-password-123"))

    def test_code_cannot_be_reused(self):
        code = self._request_code()
        self.client.post(
            "/api/auth/password-reset/confirm/",
            {"email": "jane@example.com", "code": code, "new_password": "new-password-123"},
        )
        cache.clear()

        reuse = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"email": "jane@example.com", "code": code, "new_password": "another-password"},
        )

        self.assertEqual(reuse.status_code, 400)

    def test_wrong_code_is_rejected_and_counts_as_an_attempt(self):
        self._request_code()

        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"email": "jane@example.com", "code": "000000", "new_password": "new-password-123"},
        )

        self.assertEqual(response.status_code, 400)
        reset_code = PasswordResetCode.objects.get(user=self.user)
        self.assertEqual(reset_code.attempts, 1)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("old-password"))

    def test_too_many_wrong_attempts_locks_out_the_code(self):
        self._request_code()
        reset_code = PasswordResetCode.objects.get(user=self.user)
        reset_code.attempts = PasswordResetCode.MAX_ATTEMPTS
        reset_code.save(update_fields=["attempts"])

        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"email": "jane@example.com", "code": "123456", "new_password": "new-password-123"},
        )

        self.assertEqual(response.status_code, 400)

    def test_expired_code_is_rejected(self):
        self._request_code()
        reset_code = PasswordResetCode.objects.get(user=self.user)
        reset_code.expires_at = timezone.now() - timedelta(seconds=1)
        reset_code.save(update_fields=["expires_at"])

        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"email": "jane@example.com", "code": "123456", "new_password": "new-password-123"},
        )

        self.assertEqual(response.status_code, 400)

    def test_unknown_email_gets_generic_error(self):
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"email": "nobody@example.com", "code": "123456", "new_password": "new-password-123"},
        )

        self.assertEqual(response.status_code, 400)

    def test_malformed_code_is_rejected_by_validation(self):
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"email": "jane@example.com", "code": "abc", "new_password": "new-password-123"},
        )

        self.assertEqual(response.status_code, 400)
