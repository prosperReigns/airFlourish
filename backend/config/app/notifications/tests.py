from django.contrib.auth import get_user_model
from django.test import TestCase

from app.notifications.models import Notification
from app.notifications.serializers import NotificationSerializer
from app.notifications.services import create_notification


class NotificationModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="notify@example.com",
            password="password123",
            country="NG",
        )

    def test_str_includes_title_and_user(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Welcome",
            message="Hello there",
        )
        self.assertEqual(str(notification), f"Welcome - {self.user.email}")

    def test_is_read_defaults_false(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Unread",
            message="Please read",
        )
        self.assertFalse(notification.is_read)


class NotificationSerializerTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="serialize@example.com",
            password="password123",
            country="NG",
        )
        self.notification = Notification.objects.create(
            user=self.user,
            title="Serialized",
            message="Payload",
            notification_type="success",
        )

    def test_serializer_fields(self):
        data = NotificationSerializer(self.notification).data
        self.assertEqual(data["title"], "Serialized")
        self.assertEqual(data["message"], "Payload")
        self.assertEqual(data["notification_type"], "success")
        self.assertFalse(data["is_read"])
        self.assertIn("created_at", data)


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="service@example.com",
            password="password123",
            country="NG",
        )

    def test_create_notification_creates_record(self):
        notification = create_notification(
            user=self.user,
            title="Service",
            message="Created via service",
            notification_type="info",
        )
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.title, "Service")
        self.assertEqual(notification.message, "Created via service")
        self.assertEqual(notification.notification_type, "info")
