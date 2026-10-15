from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from firebase_admin import messaging
from rest_framework.test import APIClient

from accounts.models import Customer
from .models import DeviceToken
from .services import send_push


class DeviceTokenRegisterViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="jane@example.com", password="pw")
        Customer.objects.create(user=self.user, name="Jane")
        self.client.force_authenticate(self.user)

    def test_register_creates_a_token(self):
        response = self.client.post(
            "/api/notifications/device-tokens/", {"token": "abc123", "platform": "android"},
        )

        self.assertEqual(response.status_code, 200)
        token = DeviceToken.objects.get(token="abc123")
        self.assertEqual(token.user, self.user)
        self.assertEqual(token.platform, "android")

    def test_registering_an_existing_token_reassigns_it_to_the_new_owner(self):
        other_user = User.objects.create_user(username="bob@example.com", password="pw")
        DeviceToken.objects.create(user=other_user, token="shared-device", platform="ios")

        response = self.client.post(
            "/api/notifications/device-tokens/", {"token": "shared-device", "platform": "ios"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(DeviceToken.objects.filter(token="shared-device").count(), 1)
        self.assertEqual(DeviceToken.objects.get(token="shared-device").user, self.user)

    def test_register_requires_authentication(self):
        self.client.force_authenticate(None)
        response = self.client.post(
            "/api/notifications/device-tokens/", {"token": "abc123", "platform": "android"},
        )
        self.assertEqual(response.status_code, 401)

    def test_register_rejects_an_invalid_platform(self):
        response = self.client.post(
            "/api/notifications/device-tokens/", {"token": "abc123", "platform": "windows"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(DeviceToken.objects.count(), 0)


class DeviceTokenUnregisterViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="jane@example.com", password="pw")
        Customer.objects.create(user=self.user, name="Jane")
        self.client.force_authenticate(self.user)

    def test_unregister_deletes_the_callers_own_token(self):
        DeviceToken.objects.create(user=self.user, token="abc123", platform="android")

        response = self.client.post("/api/notifications/device-tokens/unregister/", {"token": "abc123"})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(DeviceToken.objects.filter(token="abc123").exists())

    def test_unregister_cannot_delete_another_users_token(self):
        other_user = User.objects.create_user(username="bob@example.com", password="pw")
        DeviceToken.objects.create(user=other_user, token="not-mine", platform="android")

        response = self.client.post("/api/notifications/device-tokens/unregister/", {"token": "not-mine"})

        self.assertEqual(response.status_code, 200)  # idempotent-looking, but scoped
        self.assertTrue(DeviceToken.objects.filter(token="not-mine", user=other_user).exists())

    def test_unregister_a_nonexistent_token_is_a_no_op_success(self):
        response = self.client.post("/api/notifications/device-tokens/unregister/", {"token": "never-registered"})
        self.assertEqual(response.status_code, 200)


class SendPushTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jane@example.com", password="pw")
        Customer.objects.create(user=self.user, name="Jane")

    def test_send_push_is_a_no_op_when_firebase_is_not_configured(self):
        with patch("notifications.services._get_firebase_app", return_value=None):
            send_push(self.user, "title", "body")  # must not raise

    def test_send_push_swallows_any_exception_from_the_firebase_sdk(self):
        DeviceToken.objects.create(user=self.user, token="abc123", platform="android")

        with patch("notifications.services._get_firebase_app", return_value=object()), \
                patch("firebase_admin.messaging.send_each", side_effect=RuntimeError("network down")):
            send_push(self.user, "title", "body")  # must not raise

    def test_send_push_deletes_a_token_the_sdk_reports_as_unregistered(self):
        DeviceToken.objects.create(user=self.user, token="stale-token", platform="android")
        response = messaging.SendResponse(None, messaging.UnregisteredError("gone"))

        with patch("notifications.services._get_firebase_app", return_value=object()), \
                patch(
                    "firebase_admin.messaging.send_each",
                    return_value=messaging.BatchResponse([response]),
                ):
            send_push(self.user, "title", "body")

        self.assertFalse(DeviceToken.objects.filter(token="stale-token").exists())

    def test_send_push_keeps_other_tokens_when_only_one_fails(self):
        DeviceToken.objects.create(user=self.user, token="good-token", platform="android")
        DeviceToken.objects.create(user=self.user, token="stale-token", platform="ios")
        responses = [
            messaging.SendResponse({"name": "projects/x/messages/1"}, None),
            messaging.SendResponse(None, messaging.UnregisteredError("gone")),
        ]

        with patch("notifications.services._get_firebase_app", return_value=object()), \
                patch(
                    "firebase_admin.messaging.send_each",
                    return_value=messaging.BatchResponse(responses),
                ):
            send_push(self.user, "title", "body")

        self.assertTrue(DeviceToken.objects.filter(token="good-token").exists())
        self.assertFalse(DeviceToken.objects.filter(token="stale-token").exists())
