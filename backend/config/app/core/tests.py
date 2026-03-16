from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from app.core.models import IdempotencyKey


class IdempotencyKeyModelTests(TestCase):
    def test_response_body_defaults_none(self):
        key = IdempotencyKey.objects.create(
            key="idem-001",
            request_hash="hash-001",
            expires_at=timezone.now(),
        )
        self.assertIsNone(key.response_body)
        self.assertIsNone(key.status_code)

    def test_unique_key_enforced(self):
        IdempotencyKey.objects.create(
            key="idem-unique",
            request_hash="hash-unique",
            expires_at=timezone.now(),
        )
        with self.assertRaises(IntegrityError):
            IdempotencyKey.objects.create(
                key="idem-unique",
                request_hash="hash-duplicate",
                expires_at=timezone.now(),
            )

    def test_expires_at_is_set(self):
        expires_at = timezone.now()
        key = IdempotencyKey.objects.create(
            key="idem-expire",
            request_hash="hash-expire",
            expires_at=expires_at,
        )
        self.assertEqual(key.expires_at, expires_at)

    def test_request_hash_saved(self):
        key = IdempotencyKey.objects.create(
            key="idem-hash",
            request_hash="hash-value",
            expires_at=timezone.now(),
        )
        self.assertEqual(key.request_hash, "hash-value")
