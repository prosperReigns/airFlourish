from django.contrib.auth import get_user_model
from django.test import TestCase

from app.audit.models import AuditLog


class AuditLogModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="auditor@example.com",
            password="password123",
            country="NG",
        )

    def test_str_includes_actor_and_action(self):
        log = AuditLog.objects.create(actor=self.user, action="login")
        self.assertEqual(str(log), f"{self.user} -> login")

    def test_metadata_defaults_to_empty_dict(self):
        log = AuditLog.objects.create(actor=self.user, action="viewed_report")
        self.assertEqual(log.metadata, {})

    def test_ip_address_optional(self):
        log = AuditLog.objects.create(actor=self.user, action="logout", ip_address=None)
        self.assertIsNone(log.ip_address)

    def test_actor_optional(self):
        log = AuditLog.objects.create(actor=None, action="system_task")
        self.assertEqual(str(log), "None -> system_task")
