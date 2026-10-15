from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Customer, Representative
from .models import ServiceRequest, TaskStatus


class TaskLifecycleNotificationTests(TestCase):
    """
    Confirms the three rep-triggered status transitions, and admin-style
    assignment, each dispatch exactly one push to the right person —
    mocking tasks.notifications.dispatch_push so no real FCM call is made.
    """

    def setUp(self):
        self.client = APIClient()

        self.customer_user = User.objects.create_user(username="jane@example.com", password="pw")
        self.customer = Customer.objects.create(user=self.customer_user, name="Jane")

        self.rep_user = User.objects.create_user(username="rep@example.com", password="pw")
        self.rep = Representative.objects.create(user=self.rep_user, name="Rep")

        self.task = ServiceRequest.objects.create(
            requested_by=self.customer,
            service_title="Pipe repair",
            contact_number="0123456789",
            status=TaskStatus.PENDING,
        )
        self.client.force_authenticate(self.rep_user)

    def test_confirm_notifies_the_customer(self):
        with patch("tasks.notifications.dispatch_push") as mock_dispatch:
            # The task must already be assigned to this rep to confirm it.
            self.task.assigned_representative = self.rep
            self.task.save()
            mock_dispatch.reset_mock()  # ignore the assignment push triggered by that save()

            response = self.client.post(f"/api/rep/tasks/{self.task.id}/confirm/")

        self.assertEqual(response.status_code, 200)
        mock_dispatch.assert_called_once()
        args, kwargs = mock_dispatch.call_args
        self.assertEqual(args[0], self.customer_user)

    def test_start_notifies_the_customer(self):
        # Assignment and the status change must be separate save()s: the
        # existing reassignment signal always resets status to PENDING
        # whenever assigned_representative changes in the same save().
        with patch("tasks.notifications.dispatch_push"):  # ignore the assignment push
            self.task.assigned_representative = self.rep
            self.task.save()
            self.task.status = TaskStatus.CONFIRMED
            self.task.save()

        with patch("tasks.notifications.dispatch_push") as mock_dispatch:
            response = self.client.post(f"/api/rep/tasks/{self.task.id}/start/")

        self.assertEqual(response.status_code, 200)
        mock_dispatch.assert_called_once()
        self.assertEqual(mock_dispatch.call_args[0][0], self.customer_user)

    def test_complete_notifies_the_customer(self):
        with patch("tasks.notifications.dispatch_push"):  # ignore the assignment push
            self.task.assigned_representative = self.rep
            self.task.save()
            self.task.status = TaskStatus.IN_PROGRESS
            self.task.save()

        with patch("tasks.notifications.dispatch_push") as mock_dispatch:
            response = self.client.post(f"/api/rep/tasks/{self.task.id}/complete/")

        self.assertEqual(response.status_code, 200)
        mock_dispatch.assert_called_once()
        self.assertEqual(mock_dispatch.call_args[0][0], self.customer_user)

    def test_assigning_a_rep_notifies_that_rep(self):
        with patch("tasks.notifications.dispatch_push") as mock_dispatch:
            self.task.assigned_representative = self.rep
            self.task.save()

        mock_dispatch.assert_called_once()
        self.assertEqual(mock_dispatch.call_args[0][0], self.rep_user)

    def test_reassigning_to_a_different_rep_notifies_the_new_rep_only(self):
        with patch("tasks.notifications.dispatch_push"):  # ignore the first assignment push
            self.task.assigned_representative = self.rep
            self.task.save()

        other_rep_user = User.objects.create_user(username="rep2@example.com", password="pw")
        other_rep = Representative.objects.create(user=other_rep_user, name="Rep Two")

        with patch("tasks.notifications.dispatch_push") as mock_dispatch:
            self.task.assigned_representative = other_rep
            self.task.save()

        mock_dispatch.assert_called_once()
        self.assertEqual(mock_dispatch.call_args[0][0], other_rep_user)

    def test_saving_with_no_assignment_change_does_not_notify(self):
        with patch("tasks.notifications.dispatch_push"):  # ignore the assignment push
            self.task.assigned_representative = self.rep
            self.task.save()

        with patch("tasks.notifications.dispatch_push") as mock_dispatch:
            self.task.details = "updated details"
            self.task.save()

        mock_dispatch.assert_not_called()


class RepTaskDetailViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.customer_user = User.objects.create_user(username="jane@example.com", password="pw")
        self.customer = Customer.objects.create(user=self.customer_user, name="Jane")

        self.rep_user = User.objects.create_user(username="rep@example.com", password="pw")
        self.rep = Representative.objects.create(user=self.rep_user, name="Rep")

        # Creating with assigned_representative already set fires the
        # real assignment-notification signal (not what this test class
        # is about) — mock it so no background thread outlives the test.
        with patch("tasks.notifications.dispatch_push"):
            self.task = ServiceRequest.objects.create(
                requested_by=self.customer,
                service_title="Pipe repair",
                contact_number="0123456789",
                status=TaskStatus.PENDING,
                assigned_representative=self.rep,
            )
        self.client.force_authenticate(self.rep_user)

    def test_rep_can_fetch_their_own_assigned_task(self):
        response = self.client.get(f"/api/rep/tasks/{self.task.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.task.id)

    def test_fetching_a_task_assigned_to_someone_else_404s(self):
        other_rep_user = User.objects.create_user(username="rep2@example.com", password="pw")
        Representative.objects.create(user=other_rep_user, name="Rep Two")
        self.client.force_authenticate(other_rep_user)

        response = self.client.get(f"/api/rep/tasks/{self.task.id}/")
        self.assertEqual(response.status_code, 404)

    def test_fetching_a_dismissed_task_404s_since_it_clears_the_assignment(self):
        self.task.assigned_representative = None
        self.task.status = TaskStatus.DISMISSED
        self.task.save()

        response = self.client.get(f"/api/rep/tasks/{self.task.id}/")
        self.assertEqual(response.status_code, 404)
