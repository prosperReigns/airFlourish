from django.contrib.auth import get_user_model
from django.test import TestCase

from app.search_security.models import SearchLog


class SearchLogModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="search@example.com",
            password="password123",
            country="NG",
        )

    def test_allows_null_user(self):
        log = SearchLog.objects.create(
            user=None,
            ip_address="127.0.0.1",
            endpoint="/api/flights/search/",
        )
        self.assertIsNone(log.user)

    def test_endpoint_saved(self):
        log = SearchLog.objects.create(
            user=self.user,
            ip_address="127.0.0.1",
            endpoint="/api/hotels/search/",
        )
        self.assertEqual(log.endpoint, "/api/hotels/search/")

    def test_ip_address_saved(self):
        log = SearchLog.objects.create(
            user=self.user,
            ip_address="10.0.0.1",
            endpoint="/api/transport/search/",
        )
        self.assertEqual(log.ip_address, "10.0.0.1")

    def test_created_at_set(self):
        log = SearchLog.objects.create(
            user=self.user,
            ip_address="10.0.0.2",
            endpoint="/api/visa/search/",
        )
        self.assertIsNotNone(log.created_at)
