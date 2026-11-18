from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Customer, Representative
from .models import Feedback

URL = "/api/feedback/"


class FeedbackCreateViewTests(TestCase):
    def setUp(self):
        cache.clear()  # isolate from the per-user throttle
        self.client = APIClient()
        self.user = User.objects.create_user(username="jane@example.com", email="jane@example.com", password="pw")
        Customer.objects.create(user=self.user, name="Jane")
        self.client.force_authenticate(self.user)

    def test_saves_feedback_for_the_signed_in_user(self):
        response = self.client.post(
            URL, {"category": "suggestion", "message": "  Add bKash payments.  ", "source": "website"},
        )

        self.assertEqual(response.status_code, 201)
        feedback = Feedback.objects.get()
        self.assertEqual(feedback.user, self.user)
        self.assertEqual(feedback.category, "suggestion")
        self.assertEqual(feedback.message, "Add bKash payments.")
        self.assertEqual(feedback.source, "website")
        self.assertFalse(feedback.is_read)
        self.assertEqual(response.data["id"], feedback.id)

    def test_source_defaults_to_website(self):
        self.client.post(URL, {"category": "praise", "message": "Great service"})
        self.assertEqual(Feedback.objects.get().source, "website")

    def test_ignores_a_user_or_is_read_sent_by_the_client(self):
        other = User.objects.create_user(username="bob@example.com", password="pw")
        self.client.post(URL, {"category": "other", "message": "Hi", "user": other.id, "is_read": True})

        feedback = Feedback.objects.get()
        self.assertEqual(feedback.user, self.user)
        self.assertFalse(feedback.is_read)

    def test_representatives_can_send_feedback(self):
        rep = User.objects.create_user(username="rep@example.com", password="pw")
        Representative.objects.create(user=rep, name="Rahim")
        self.client.force_authenticate(rep)

        response = self.client.post(URL, {"category": "problem", "message": "Task list is slow", "source": "representative_app"})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Feedback.objects.get().user, rep)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        response = self.client.post(URL, {"category": "other", "message": "Hi"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_rejects_a_blank_message(self):
        response = self.client.post(URL, {"category": "other", "message": "   "})
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_rejects_a_message_over_the_limit(self):
        response = self.client.post(URL, {"category": "other", "message": "x" * (Feedback.MESSAGE_MAX_LENGTH + 1)})
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_requires_a_valid_category(self):
        for data in ({"message": "Hi"}, {"category": "complaint", "message": "Hi"}):
            response = self.client.post(URL, data)
            self.assertEqual(response.status_code, 400)
            self.assertIn("category", response.data)

    def test_is_throttled_per_user(self):
        for _ in range(10):
            self.assertEqual(self.client.post(URL, {"category": "other", "message": "Hi"}).status_code, 201)
        self.assertEqual(self.client.post(URL, {"category": "other", "message": "Hi"}).status_code, 429)


class FeedbackAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin", email="admin@example.com", password="pw")
        self.client.force_login(self.admin)
        sender = User.objects.create_user(username="jane@example.com", email="jane@example.com", password="pw")
        self.feedback = Feedback.objects.create(user=sender, category="problem", message="The page froze")

    def test_list_and_detail_pages_load(self):
        listing = self.client.get("/admin/feedback/feedback/")
        self.assertContains(listing, "jane@example.com")
        self.assertContains(listing, "The page froze")
        detail = self.client.get(f"/admin/feedback/feedback/{self.feedback.id}/change/")
        self.assertContains(detail, "The page froze")

    def test_mark_read_action(self):
        self.client.post("/admin/feedback/feedback/", {
            "action": "mark_read", "_selected_action": [self.feedback.id],
        })
        self.feedback.refresh_from_db()
        self.assertTrue(self.feedback.is_read)

    def test_keeps_feedback_when_the_sender_is_deleted(self):
        self.feedback.user.delete()
        self.feedback.refresh_from_db()
        self.assertIsNone(self.feedback.user)
        self.assertContains(self.client.get("/admin/feedback/feedback/"), "(deleted user)")
