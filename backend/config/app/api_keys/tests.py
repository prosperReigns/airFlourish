from django.test import TestCase

from app.api_keys.models import APIKey


class APIKeyModelTests(TestCase):
    def test_key_generated_when_missing(self):
        api_key = APIKey.objects.create(name="Primary Key")
        self.assertTrue(api_key.key)
        self.assertEqual(len(api_key.key), 64)

    def test_key_preserved_when_provided(self):
        api_key = APIKey.objects.create(name="Custom Key", key="custom-key")
        self.assertEqual(api_key.key, "custom-key")

    def test_default_active_true(self):
        api_key = APIKey.objects.create(name="Active Key")
        self.assertTrue(api_key.active)

    def test_default_rate_limit(self):
        api_key = APIKey.objects.create(name="Rate Key")
        self.assertEqual(api_key.rate_limit, 1000)

    def test_str_returns_name(self):
        api_key = APIKey.objects.create(name="Readable Key")
        self.assertEqual(str(api_key), "Readable Key")
