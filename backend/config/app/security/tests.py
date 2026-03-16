from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from app.security.models import BlockedIP, PaymentAttempt


class SecurityModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="security@example.com",
            password="password123",
            country="NG",
        )

    def test_blocked_ip_unique(self):
        BlockedIP.objects.create(ip_address="192.168.0.1", reason="abuse")
        with self.assertRaises(IntegrityError):
            BlockedIP.objects.create(ip_address="192.168.0.1", reason="duplicate")

    def test_payment_attempt_defaults_success_false(self):
        attempt = PaymentAttempt.objects.create(user=self.user)
        self.assertFalse(attempt.success)

    def test_payment_attempt_user_saved(self):
        attempt = PaymentAttempt.objects.create(user=self.user, success=True)
        self.assertEqual(attempt.user, self.user)

    def test_blocked_ip_reason_saved(self):
        blocked = BlockedIP.objects.create(ip_address="10.10.0.1", reason="rate limit")
        self.assertEqual(blocked.reason, "rate limit")
