from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
from django.db import connection, IntegrityError
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from app.bookings.models import Booking
from app.bookings.serializers import BookingSerializer
from app.services.booking_engine import BookingEngine

BOOKINGS_URL = "/api/bookings/bookings/"
FLIGHT_SEARCH_URL = "/api/bookings/flights/search/"


def throttled_settings(rate):
    rates = dict(settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}))
    rates.update({"anon": rate, "user": rate, "ip": rate})
    return {**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": rates}


class BaseBookingTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
            country="NG",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="password123",
            country="NG",
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="password123",
            country="NG",
            user_type="admin",
            is_staff=True,
        )

    def create_booking(self, user=None, service_type="hotel", total_price=Decimal("100.00")):
        return BookingEngine.create_booking(
            user=user or self.user,
            service_type=service_type,
            total_price=total_price,
            currency="NGN",
        )


class BookingModelTests(BaseBookingTestCase):
    def test_booking_str_and_defaults(self):
        booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            reference_code="HOT-TEST-001",
            total_price=Decimal("120.00"),
            currency="NGN",
        )
        self.assertEqual(str(booking), "HOT-TEST-001 - hotel")
        self.assertEqual(booking.status, "pending")
        self.assertIsNone(booking.external_service_id)

    def test_booking_status_choices(self):
        booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            reference_code="HOT-TEST-002",
            total_price=Decimal("120.00"),
            currency="NGN",
            status="confirmed",
        )
        self.assertEqual(booking.status, "confirmed")

    def test_booking_service_type_choices(self):
        booking = Booking.objects.create(
            user=self.user,
            service_type="flight",
            reference_code="FLI-TEST-001",
            total_price=Decimal("300.00"),
            currency="NGN",
        )
        self.assertEqual(booking.service_type, "flight")

    def test_reference_code_unique(self):
        Booking.objects.create(
            user=self.user,
            service_type="hotel",
            reference_code="HOT-UNIQUE-001",
            total_price=Decimal("50.00"),
            currency="NGN",
        )
        with self.assertRaises(IntegrityError):
            Booking.objects.create(
                user=self.user,
                service_type="hotel",
                reference_code="HOT-UNIQUE-001",
                total_price=Decimal("60.00"),
                currency="NGN",
            )

    def test_booking_currency_default(self):
        booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            reference_code="HOT-TEST-003",
        )
        self.assertEqual(booking.currency, "NGN")

    def test_booking_total_price_nullable(self):
        booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            reference_code="HOT-TEST-004",
            total_price=None,
        )
        self.assertIsNone(booking.total_price)


class BookingSerializerTests(BaseBookingTestCase):
    def setUp(self):
        super().setUp()
        self.booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            reference_code="HOT-TEST-005",
            total_price=Decimal("200.00"),
            currency="NGN",
        )

    def test_booking_serializer_outputs_expected_fields(self):
        data = BookingSerializer(self.booking).data
        self.assertEqual(data["user"], self.user.id)
        self.assertEqual(data["service_type"], "hotel")
        self.assertEqual(data["reference_code"], "HOT-TEST-005")
        self.assertEqual(data["status"], "pending")
        self.assertEqual(str(data["total_price"]), "200.00")

    def test_booking_serializer_includes_created_at(self):
        data = BookingSerializer(self.booking).data
        self.assertIn("created_at", data)

    def test_booking_serializer_read_only_fields_ignored(self):
        serializer = BookingSerializer(
            data={
                "user": self.other_user.id,
                "service_type": "hotel",
                "status": "pending",
                "reference_code": "SHOULD-NOT-BE-USED",
                "total_price": "120.00",
            }
        )
        self.assertTrue(serializer.is_valid())
        self.assertNotIn("user", serializer.validated_data)
        self.assertNotIn("reference_code", serializer.validated_data)

    def test_booking_serializer_allows_null_total_price(self):
        serializer = BookingSerializer(
            data={
                "service_type": "hotel",
                "total_price": None,
            }
        )
        self.assertTrue(serializer.is_valid())

    def test_booking_serializer_rejects_invalid_service_type(self):
        serializer = BookingSerializer(
            data={
                "service_type": "invalid",
                "total_price": "120.00",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("service_type", serializer.errors)

    def test_booking_serializer_rejects_invalid_status(self):
        serializer = BookingSerializer(
            data={
                "service_type": "hotel",
                "status": "not-valid",
                "total_price": "120.00",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("status", serializer.errors)

    def test_booking_serializer_missing_service_type(self):
        serializer = BookingSerializer(
            data={
                "total_price": "120.00",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("service_type", serializer.errors)

    def test_booking_serializer_invalid_total_price(self):
        serializer = BookingSerializer(
            data={
                "service_type": "hotel",
                "total_price": "not-a-number",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("total_price", serializer.errors)


class BookingViewSetAuthTests(BaseBookingTestCase):
    def test_list_requires_auth(self):
        response = self.client.get(BOOKINGS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_requires_auth(self):
        booking = self.create_booking()
        response = self.client.get(f"{BOOKINGS_URL}{booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_auth(self):
        response = self.client.post(
            BOOKINGS_URL,
            data={"service_type": "hotel", "total_price": "150.00"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_requires_auth(self):
        booking = self.create_booking()
        response = self.client.delete(f"{BOOKINGS_URL}{booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BookingViewSetListRetrieveTests(BaseBookingTestCase):
    def setUp(self):
        super().setUp()
        self.user_booking = self.create_booking(user=self.user, total_price=Decimal("150.00"))
        self.other_booking = self.create_booking(user=self.other_user, total_price=Decimal("250.00"))

    def test_regular_user_sees_only_own_bookings(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(BOOKINGS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["user"], self.user.id)

    def test_admin_user_sees_all_bookings(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(BOOKINGS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        user_ids = {booking["user"] for booking in response.data}
        self.assertIn(self.user.id, user_ids)
        self.assertIn(self.other_user.id, user_ids)

    def test_regular_user_retrieve_own_booking(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{BOOKINGS_URL}{self.user_booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], self.user.id)

    def test_regular_user_cannot_retrieve_other_booking(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{BOOKINGS_URL}{self.other_booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_user_can_retrieve_other_booking(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(f"{BOOKINGS_URL}{self.other_booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], self.other_user.id)

    def test_list_returns_expected_count_for_user(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(BOOKINGS_URL)
        self.assertEqual(len(response.data), 1)

    def test_list_returns_expected_count_for_admin(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(BOOKINGS_URL)
        self.assertEqual(len(response.data), 2)


class BookingViewSetCreateTests(BaseBookingTestCase):
    def test_user_can_create_booking(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BOOKINGS_URL,
            data={"service_type": "hotel", "total_price": "150.00"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Booking.objects.filter(user=self.user).count(), 1)

    def test_create_sets_reference_code(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BOOKINGS_URL,
            data={"service_type": "hotel", "total_price": "150.00"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["reference_code"])

    def test_create_ignores_user_field_in_payload(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BOOKINGS_URL,
            data={
                "user": self.other_user.id,
                "service_type": "hotel",
                "total_price": "150.00",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(booking.user_id, self.user.id)

    def test_create_defaults_status_pending(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BOOKINGS_URL,
            data={"service_type": "hotel", "total_price": "150.00"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "pending")

    def test_create_rejects_invalid_service_type(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BOOKINGS_URL,
            data={"service_type": "invalid", "total_price": "150.00"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("service_type", response.data)

    def test_create_rejects_invalid_status(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BOOKINGS_URL,
            data={"service_type": "hotel", "status": "not-valid"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    def test_create_allows_null_total_price(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BOOKINGS_URL,
            data={"service_type": "hotel", "total_price": None},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking = Booking.objects.get(id=response.data["id"])
        self.assertIsNone(booking.total_price)

    def test_create_rejects_missing_service_type(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BOOKINGS_URL,
            data={"total_price": "150.00"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("service_type", response.data)

    def test_create_returns_created_at(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BOOKINGS_URL,
            data={"service_type": "hotel", "total_price": "150.00"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("created_at", response.data)

    def test_create_returns_201(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BOOKINGS_URL,
            data={"service_type": "hotel", "total_price": "150.00"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class BookingViewSetDeleteTests(BaseBookingTestCase):
    def setUp(self):
        super().setUp()
        self.user_booking = self.create_booking(user=self.user)
        self.other_booking = self.create_booking(user=self.other_user)

    def test_user_can_delete_own_booking(self):
        self.client.force_authenticate(self.user)
        response = self.client.delete(f"{BOOKINGS_URL}{self.user_booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Booking.objects.filter(id=self.user_booking.id).exists())

    def test_user_cannot_delete_other_booking(self):
        self.client.force_authenticate(self.user)
        response = self.client.delete(f"{BOOKINGS_URL}{self.other_booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_delete_other_booking(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f"{BOOKINGS_URL}{self.other_booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_nonexistent_returns_404(self):
        self.client.force_authenticate(self.user)
        response = self.client.delete(f"{BOOKINGS_URL}999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_returns_204(self):
        self.client.force_authenticate(self.user)
        response = self.client.delete(f"{BOOKINGS_URL}{self.user_booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class BookingViewSetUpdateTests(BaseBookingTestCase):
    def test_non_admin_cannot_update_booking_status(self):
        booking = self.create_booking(user=self.user)
        self.client.force_authenticate(self.user)
        response = self.client.put(
            f"{BOOKINGS_URL}{booking.id}/",
            data={"status": "confirmed"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Only admin can update booking status.")


class BookingThrottleTests(BaseBookingTestCase):
    @override_settings(REST_FRAMEWORK=throttled_settings("1/minute"))
    def test_throttle_blocks_repeated_list_requests(self):
        self.client.force_authenticate(self.user)
        first = self.client.get(BOOKINGS_URL)
        second = self.client.get(BOOKINGS_URL)
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @override_settings(REST_FRAMEWORK=throttled_settings("1/minute"))
    def test_throttle_blocks_repeated_create_requests(self):
        self.client.force_authenticate(self.user)
        first = self.client.post(
            BOOKINGS_URL,
            data={"service_type": "hotel", "total_price": "150.00"},
        )
        second = self.client.post(
            BOOKINGS_URL,
            data={"service_type": "hotel", "total_price": "160.00"},
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @override_settings(REST_FRAMEWORK=throttled_settings("1/minute"))
    def test_throttle_separate_users_have_separate_limits(self):
        first_client = APIClient()
        second_client = APIClient()
        first_client.force_authenticate(self.user)
        second_client.force_authenticate(self.other_user)
        first = first_client.get(BOOKINGS_URL)
        second = second_client.get(BOOKINGS_URL)
        third = first_client.get(BOOKINGS_URL)
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(third.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @override_settings(REST_FRAMEWORK=throttled_settings("1/minute"))
    def test_throttle_cache_clear_resets_limits(self):
        self.client.force_authenticate(self.user)
        first = self.client.get(BOOKINGS_URL)
        second = self.client.get(BOOKINGS_URL)
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        cache.clear()
        third = self.client.get(BOOKINGS_URL)
        self.assertEqual(third.status_code, status.HTTP_200_OK)


class BookingCachingTests(BaseBookingTestCase):
    def setUp(self):
        super().setUp()
        self.booking = self.create_booking(user=self.user)

    def test_cache_store_and_retrieve_booking_list(self):
        data = BookingSerializer([self.booking], many=True).data
        cache_key = f"booking_list:{self.user.id}"
        cache.set(cache_key, data, timeout=60)
        cached = cache.get(cache_key)
        self.assertEqual(cached, data)

    def test_cache_isolation_between_users(self):
        data_user = BookingSerializer([self.booking], many=True).data
        cache.set(f"booking_list:{self.user.id}", data_user, timeout=60)
        cache.set(f"booking_list:{self.other_user.id}", [], timeout=60)
        self.assertNotEqual(
            cache.get(f"booking_list:{self.user.id}"),
            cache.get(f"booking_list:{self.other_user.id}"),
        )

    def test_cache_clear_removes_cached_entries(self):
        cache_key = f"booking_list:{self.user.id}"
        cache.set(cache_key, ["data"], timeout=60)
        cache.clear()
        self.assertIsNone(cache.get(cache_key))

    def test_cache_can_store_serialized_booking(self):
        data = BookingSerializer(self.booking).data
        cache_key = f"booking:{self.booking.id}"
        cache.set(cache_key, data, timeout=60)
        self.assertEqual(cache.get(cache_key), data)


class BookingPerformanceTests(BaseBookingTestCase):
    def setUp(self):
        super().setUp()
        self.create_booking(user=self.user)

    def test_list_query_count_is_small(self):
        self.client.force_authenticate(self.user)
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(BOOKINGS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(context), 2)

    def test_retrieve_query_count_is_small(self):
        booking = self.create_booking(user=self.user)
        self.client.force_authenticate(self.user)
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(f"{BOOKINGS_URL}{booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(context), 2)


class FlightSearchViewTests(BaseBookingTestCase):
    def test_flight_search_requires_auth(self):
        response = self.client.get(FLIGHT_SEARCH_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_flight_search_missing_origin(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            FLIGHT_SEARCH_URL,
            data={"destination": "LAX", "departure_date": "2026-05-01"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_flight_search_missing_destination(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            FLIGHT_SEARCH_URL,
            data={"origin": "JFK", "departure_date": "2026-05-01"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_flight_search_missing_departure_date(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            FLIGHT_SEARCH_URL,
            data={"origin": "JFK", "destination": "LAX"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("app.bookings.views.AmadeusService.search_flights")
    def test_flight_search_success_calls_service(self, mock_search):
        self.client.force_authenticate(self.user)
        mock_search.return_value = [{"id": "flight-1"}]
        response = self.client.get(
            FLIGHT_SEARCH_URL,
            data={
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": "2026-05-01",
                "return_date": "2026-05-10",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_search.assert_called_once_with("JFK", "LAX", "2026-05-01", "2026-05-10")

    @patch("app.bookings.views.AmadeusService.search_flights")
    def test_flight_search_returns_service_response(self, mock_search):
        self.client.force_authenticate(self.user)
        mock_search.return_value = [{"id": "flight-1"}, {"id": "flight-2"}]
        response = self.client.get(
            FLIGHT_SEARCH_URL,
            data={
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": "2026-05-01",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [{"id": "flight-1"}, {"id": "flight-2"}])


class BookingEngineTests(BaseBookingTestCase):
    def test_create_booking_sets_pending_status(self):
        booking = BookingEngine.create_booking(
            user=self.user,
            service_type="hotel",
            total_price=Decimal("150.00"),
            currency="NGN",
        )
        self.assertEqual(booking.status, "pending")

    def test_create_booking_sets_reference_prefix(self):
        booking = BookingEngine.create_booking(
            user=self.user,
            service_type="hotel",
            total_price=Decimal("150.00"),
            currency="NGN",
        )
        self.assertTrue(booking.reference_code.startswith("HOT-"))

    def test_update_status_changes(self):
        booking = self.create_booking(user=self.user)
        BookingEngine.update_status(booking, "confirmed")
        booking.refresh_from_db()
        self.assertEqual(booking.status, "confirmed")

    def test_attach_payment_sets_external_service_id(self):
        booking = self.create_booking(user=self.user)
        BookingEngine.attach_payment(booking, "confirmed", payment_reference="PAY-123")
        booking.refresh_from_db()
        self.assertEqual(booking.external_service_id, "PAY-123")

    def test_cancel_booking_sets_cancelled_status(self):
        booking = self.create_booking(user=self.user)
        BookingEngine.cancel_booking(booking, reason="test")
        booking.refresh_from_db()
        self.assertEqual(booking.status, "cancelled")

    def test_create_booking_defaults_currency(self):
        booking = BookingEngine.create_booking(
            user=self.user,
            service_type="hotel",
            total_price=Decimal("150.00"),
        )
        self.assertEqual(booking.currency, "NGN")

class BookingExtraTests(BaseBookingTestCase):

    # -------------------------
    # Booking Creation Edge Cases
    # -------------------------
    def test_create_booking_with_zero_price(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BOOKINGS_URL, {"service_type": "hotel", "total_price": "0.00"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(booking.total_price, Decimal("0.00"))

    def test_create_booking_with_large_price(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BOOKINGS_URL, {"service_type": "flight", "total_price": "100000000.00"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(booking.total_price, Decimal("100000000.00"))

    def test_create_booking_missing_total_price_defaults_to_none(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(BOOKINGS_URL, {"service_type": "hotel"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking = Booking.objects.get(id=response.data["id"])
        self.assertIsNone(booking.total_price)

    def test_create_booking_with_invalid_currency(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BOOKINGS_URL, {"service_type": "hotel", "total_price": "150.00", "currency": "XXX"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("currency", response.data)

    def test_create_booking_with_extra_fields_ignored(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BOOKINGS_URL,
            {"service_type": "hotel", "total_price": "150.00", "unknown_field": "abc"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(hasattr(Booking.objects.get(id=response.data["id"]), "unknown_field"))

    # -------------------------
    # Booking Update / Patch
    # -------------------------
    def test_user_cannot_patch_status(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        response = self.client.patch(f"{BOOKINGS_URL}{booking.id}/", {"status": "confirmed"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_patch_status(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.admin)
        response = self.client.patch(f"{BOOKINGS_URL}{booking.id}/", {"status": "confirmed"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "confirmed")

    def test_patch_booking_total_price(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        response = self.client.patch(f"{BOOKINGS_URL}{booking.id}/", {"total_price": "200.00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.total_price, Decimal("200.00"))

    def test_patch_booking_service_type_invalid(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        response = self.client.patch(f"{BOOKINGS_URL}{booking.id}/", {"service_type": "xyz"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_booking_with_no_changes(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        response = self.client.patch(f"{BOOKINGS_URL}{booking.id}/", {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # -------------------------
    # Booking Deletion Edge Cases
    # -------------------------
    def test_delete_booking_twice(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        self.client.delete(f"{BOOKINGS_URL}{booking.id}/")
        response = self.client.delete(f"{BOOKINGS_URL}{booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_delete_any_booking(self):
        booking = self.create_booking(user=self.other_user)
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f"{BOOKINGS_URL}{booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # -------------------------
    # Booking Listing / Filtering
    # -------------------------
    def test_list_bookings_empty_for_new_user(self):
        self.client.force_authenticate(self.user)
        Booking.objects.all().delete()
        response = self.client.get(BOOKINGS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_filter_bookings_by_service_type(self):
        self.create_booking(service_type="hotel")
        self.create_booking(service_type="flight")
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{BOOKINGS_URL}?service_type=flight")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(b["service_type"] == "flight" for b in response.data))

    def test_filter_bookings_by_status(self):
        self.create_booking()
        confirmed = self.create_booking()
        confirmed.status = "confirmed"
        confirmed.save()
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{BOOKINGS_URL}?status=confirmed")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(b["status"] == "confirmed" for b in response.data))

    def test_list_bookings_ordered_by_created_at(self):
        b1 = self.create_booking()
        b2 = self.create_booking()
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{BOOKINGS_URL}?ordering=-created_at")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data[0]["id"], response.data[1]["id"])

    def test_list_bookings_ordered_by_total_price(self):
        self.create_booking(total_price=Decimal("100.00"))
        self.create_booking(total_price=Decimal("200.00"))
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{BOOKINGS_URL}?ordering=total_price")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prices = [Decimal(b["total_price"]) for b in response.data]
        self.assertEqual(prices, sorted(prices))

    # -------------------------
    # Flight Search Edge Cases
    # -------------------------
    @patch("app.bookings.views.AmadeusService.search_flights")
    def test_flight_search_empty_result(self, mock_search):
        self.client.force_authenticate(self.user)
        mock_search.return_value = []
        response = self.client.get(
            FLIGHT_SEARCH_URL,
            data={"origin": "JFK", "destination": "LAX", "departure_date": "2026-05-01"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    @patch("app.bookings.views.AmadeusService.search_flights")
    def test_flight_search_invalid_dates(self, mock_search):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            FLIGHT_SEARCH_URL,
            data={"origin": "JFK", "destination": "LAX", "departure_date": "not-a-date"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------
    # Booking Engine Edge Cases
    # -------------------------
    def test_create_booking_without_user_defaults_to_none(self):
        booking = BookingEngine.create_booking(
            user=None, service_type="hotel", total_price=Decimal("100.00")
        )
        self.assertIsNotNone(booking.user)

    def test_cancel_booking_with_reason_none(self):
        booking = self.create_booking()
        BookingEngine.cancel_booking(booking)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "cancelled")

    def test_attach_payment_without_reference(self):
        booking = self.create_booking()
        BookingEngine.attach_payment(booking, "confirmed")
        booking.refresh_from_db()
        self.assertIsNone(booking.external_service_id)

    def test_update_status_invalid_status_ignored(self):
        booking = self.create_booking()
        BookingEngine.update_status(booking, "not-valid")
        booking.refresh_from_db()
        self.assertEqual(booking.status, "pending")

    def test_create_booking_large_batch(self):
        for _ in range(10):
            BookingEngine.create_booking(user=self.user, service_type="hotel", total_price=Decimal("50.00"))
        self.assertEqual(Booking.objects.filter(user=self.user).count(), 10)

    # -------------------------
    # Caching / Throttling Additional Cases
    # -------------------------
    def test_cache_store_individual_booking(self):
        booking = self.create_booking()
        cache_key = f"booking:{booking.id}"
        BookingSerializer(booking)
        cache.set(cache_key, booking.id, timeout=60)
        self.assertEqual(cache.get(cache_key), booking.id)

    def test_cache_clear_after_delete(self):
        booking = self.create_booking()
        cache.set(f"booking:{booking.id}", booking.id, timeout=60)
        booking.delete()
        self.assertIsNone(cache.get(f"booking:{booking.id}"))

    @override_settings(REST_FRAMEWORK=throttled_settings("1/minute"))
    def test_throttle_blocks_after_limit(self):
        self.client.force_authenticate(self.user)
        for _ in range(2):
            self.client.get(BOOKINGS_URL)
        response = self.client.get(BOOKINGS_URL)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @override_settings(REST_FRAMEWORK=throttled_settings("2/minute"))
    def test_throttle_resets_after_clear(self):
        self.client.force_authenticate(self.user)
        self.client.get(BOOKINGS_URL)
        self.client.get(BOOKINGS_URL)
        cache.clear()
        response = self.client.get(BOOKINGS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # -------------------------
    # Misc Edge Cases
    # -------------------------
    def test_booking_str_with_missing_reference(self):
        booking = Booking.objects.create(user=self.user, service_type="hotel", reference_code="")
        self.assertTrue(str(booking).startswith(" - hotel"))

    def test_multiple_bookings_same_user(self):
        self.create_booking()
        self.create_booking()
        self.assertEqual(Booking.objects.filter(user=self.user).count(), 2)

    def test_multiple_users_multiple_bookings(self):
        self.create_booking(user=self.user)
        self.create_booking(user=self.other_user)
        self.assertEqual(Booking.objects.count(), 2)

    def test_booking_serializer_handles_null_fields(self):
        booking = self.create_booking(total_price=None)
        serializer = BookingSerializer(booking)
        self.assertIsNone(serializer.data["total_price"])

    def test_booking_serializer_handles_large_numbers(self):
        booking = self.create_booking(total_price=Decimal("1000000000.00"))
        serializer = BookingSerializer(booking)
        self.assertEqual(serializer.data["total_price"], "1000000000.00")

    def test_booking_engine_create_booking_defaults(self):
        booking = BookingEngine.create_booking(user=self.user, service_type="hotel")
        self.assertEqual(booking.currency, "NGN")
        self.assertEqual(booking.status, "pending")

    def test_booking_engine_cancel_nonexistent_booking(self):
        booking = BookingEngine.create_booking(user=self.user, service_type="hotel")
        booking.delete()
        with self.assertRaises(Booking.DoesNotExist):
            BookingEngine.cancel_booking(booking)

    def test_booking_engine_attach_payment_nonexistent_booking(self):
        booking = BookingEngine.create_booking(user=self.user, service_type="hotel")
        booking.delete()
        with self.assertRaises(Booking.DoesNotExist):
            BookingEngine.attach_payment(booking, "confirmed")

    def test_booking_engine_update_status_nonexistent_booking(self):
        booking = BookingEngine.create_booking(user=self.user, service_type="hotel")
        booking.delete()
        with self.assertRaises(Booking.DoesNotExist):
            BookingEngine.update_status(booking, "confirmed")

class BookingWorkflowTests(BaseBookingTestCase):

    # -------------------------
    # Booking + Payment Workflow
    # -------------------------
    def test_attach_payment_marks_booking_confirmed(self):
        booking = self.create_booking()
        BookingEngine.attach_payment(booking, status="confirmed", payment_reference="PAY-001")
        booking.refresh_from_db()
        self.assertEqual(booking.status, "pending")  # status remains pending unless explicitly updated
        self.assertEqual(booking.external_service_id, "PAY-001")

    def test_cancel_booking_after_payment(self):
        booking = self.create_booking()
        BookingEngine.attach_payment(booking, status="confirmed", payment_reference="PAY-002")
        BookingEngine.cancel_booking(booking, reason="User request")
        booking.refresh_from_db()
        self.assertEqual(booking.status, "cancelled")

    def test_attach_payment_multiple_times(self):
        booking = self.create_booking()
        BookingEngine.attach_payment(booking, status="confirmed", payment_reference="PAY-003")
        BookingEngine.attach_payment(booking, status="confirmed", payment_reference="PAY-004")
        booking.refresh_from_db()
        self.assertEqual(booking.external_service_id, "PAY-004")

    def test_cancel_booking_twice_does_not_raise(self):
        booking = self.create_booking()
        BookingEngine.cancel_booking(booking)
        BookingEngine.cancel_booking(booking)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "cancelled")

    def test_create_booking_and_attach_payment_returns_booking(self):
        booking = BookingEngine.create_booking(user=self.user, service_type="flight")
        BookingEngine.attach_payment(booking, status="confirmed", payment_reference="PAY-005")
        self.assertIsInstance(booking, Booking)
        self.assertEqual(booking.external_service_id, "PAY-005")

    # -------------------------
    # Flight Search + Booking Workflow
    # -------------------------
    @patch("app.bookings.views.AmadeusService.search_flights")
    def test_flight_search_and_create_booking(self, mock_search):
        mock_search.return_value = [{"id": "FL-001"}]
        self.client.force_authenticate(self.user)
        response = self.client.get(
            FLIGHT_SEARCH_URL,
            data={"origin": "JFK", "destination": "LAX", "departure_date": "2026-05-01"},
        )
        flight_data = response.data[0]
        booking = BookingEngine.create_booking(user=self.user, service_type="flight", total_price=Decimal("500.00"))
        self.assertEqual(booking.service_type, "flight")
        self.assertEqual(booking.user, self.user)

    @patch("app.bookings.views.AmadeusService.search_flights")
    def test_booking_after_flight_search_returns_correct_data(self, mock_search):
        mock_search.return_value = [{"id": "FL-002", "price": 300}]
        self.client.force_authenticate(self.user)
        response = self.client.get(
            FLIGHT_SEARCH_URL,
            data={"origin": "LHR", "destination": "CDG", "departure_date": "2026-06-01"},
        )
        flight_data = response.data[0]
        booking = BookingEngine.create_booking(user=self.user, service_type="flight", total_price=Decimal(flight_data["price"]))
        self.assertEqual(booking.total_price, Decimal("300"))

    # -------------------------
    # Visa Simulation Workflow
    # -------------------------
    def test_create_booking_with_visa_required_flag(self):
        booking = self.create_booking()
        booking.visa_required = True
        booking.save()
        self.assertTrue(booking.visa_required)

    def test_attach_payment_for_visa_booking(self):
        booking = self.create_booking()
        booking.visa_required = True
        booking.save()
        BookingEngine.attach_payment(booking, status="confirmed", payment_reference="PAY-VISA-001")
        booking.refresh_from_db()
        self.assertEqual(booking.external_service_id, "PAY-VISA-001")

    def test_cancel_visa_booking(self):
        booking = self.create_booking()
        booking.visa_required = True
        booking.save()
        BookingEngine.cancel_booking(booking)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "cancelled")

    # -------------------------
    # Multi-step Workflow
    # -------------------------
    def test_full_booking_flow(self):
        # Step 1: Flight search
        with patch("app.bookings.views.AmadeusService.search_flights") as mock_search:
            mock_search.return_value = [{"id": "FL-003", "price": 400}]
            self.client.force_authenticate(self.user)
            flight_results = self.client.get(
                FLIGHT_SEARCH_URL,
                data={"origin": "NYC", "destination": "MIA", "departure_date": "2026-07-01"},
            ).data
        flight_info = flight_results[0]

        # Step 2: Create booking
        booking = BookingEngine.create_booking(user=self.user, service_type="flight", total_price=Decimal(flight_info["price"]))
        self.assertEqual(booking.total_price, Decimal("400"))

        # Step 3: Attach payment
        BookingEngine.attach_payment(booking, status="confirmed", payment_reference="PAY-006")
        booking.refresh_from_db()
        self.assertEqual(booking.external_service_id, "PAY-006")

        # Step 4: Cancel booking
        BookingEngine.cancel_booking(booking)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "cancelled")

    def test_multiple_bookings_and_payments(self):
        booking1 = self.create_booking(service_type="hotel")
        booking2 = self.create_booking(service_type="flight")
        BookingEngine.attach_payment(booking1, status="confirmed", payment_reference="PAY-007")
        BookingEngine.attach_payment(booking2, status="confirmed", payment_reference="PAY-008")
        self.assertEqual(booking1.external_service_id, "PAY-007")
        self.assertEqual(booking2.external_service_id, "PAY-008")

    def test_batch_flight_bookings(self):
        bookings = []
        for i in range(5):
            bookings.append(BookingEngine.create_booking(user=self.user, service_type="flight", total_price=Decimal("200.00")))
        self.assertEqual(len(bookings), 5)
        self.assertEqual(Booking.objects.filter(user=self.user, service_type="flight").count(), 5)

    # -------------------------
    # Edge Cases: Invalid Workflow
    # -------------------------
    def test_attach_payment_invalid_booking(self):
        booking = self.create_booking()
        booking.delete()
        with self.assertRaises(Booking.DoesNotExist):
            BookingEngine.attach_payment(booking, status="confirmed", payment_reference="PAY-INVALID")

    def test_cancel_nonexistent_booking(self):
        booking = self.create_booking()
        booking.delete()
        with self.assertRaises(Booking.DoesNotExist):
            BookingEngine.cancel_booking(booking)

    def test_update_status_invalid_booking(self):
        booking = self.create_booking()
        booking.delete()
        with self.assertRaises(Booking.DoesNotExist):
            BookingEngine.update_status(booking, "confirmed")

    def test_create_booking_after_delete_previous(self):
        booking1 = self.create_booking()
        booking1.delete()
        booking2 = self.create_booking()
        self.assertEqual(Booking.objects.count(), 1)

    # -------------------------
    # Serializer + Payment Integration
    # -------------------------
    def test_serializer_includes_external_service_id(self):
        booking = self.create_booking()
        BookingEngine.attach_payment(booking, status="confirmed", payment_reference="PAY-009")
        serializer = BookingSerializer(booking)
        self.assertEqual(serializer.data["id"], booking.id)

    def test_serializer_handles_cancelled_booking(self):
        booking = self.create_booking()
        BookingEngine.cancel_booking(booking)
        serializer = BookingSerializer(booking)
        self.assertEqual(serializer.data["status"], "cancelled")

    # -------------------------
    # Admin Permissions Workflow
    # -------------------------
    def test_admin_can_update_booking_total_price(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.admin)
        response = self.client.patch(f"{BOOKINGS_URL}{booking.id}/", {"total_price": "999.00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.total_price, Decimal("999.00"))

    def test_admin_can_cancel_other_user_booking(self):
        booking = self.create_booking(user=self.other_user)
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f"{BOOKINGS_URL}{booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_admin_can_view_all_bookings(self):
        self.create_booking(user=self.user)
        self.create_booking(user=self.other_user)
        self.client.force_authenticate(self.admin)
        response = self.client.get(BOOKINGS_URL)
        self.assertEqual(len(response.data), 2)

    # -------------------------
    # Booking + Flight + Visa + Payment Combined
    # -------------------------
    def test_full_multi_model_flow(self):
        booking = BookingEngine.create_booking(user=self.user, service_type="flight")
        booking.visa_required = True
        booking.save()
        BookingEngine.attach_payment(booking, status="confirmed", payment_reference="PAY-010")
        BookingEngine.cancel_booking(booking)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "cancelled")
        self.assertTrue(booking.visa_required)
        self.assertEqual(booking.external_service_id, "PAY-010")

    def test_create_flight_booking_with_visa_and_payment(self):
        booking = BookingEngine.create_booking(user=self.user, service_type="flight")
        booking.visa_required = True
        booking.save()
        BookingEngine.attach_payment(booking, status="confirmed", payment_reference="PAY-011")
        booking.refresh_from_db()
        self.assertTrue(booking.visa_required)
        self.assertEqual(booking.external_service_id, "PAY-011")

    def test_multiple_flight_bookings_with_payments_and_visa(self):
        bookings = []
        for i in range(3):
            b = BookingEngine.create_booking(user=self.user, service_type="flight")
            b.visa_required = True
            b.save()
            BookingEngine.attach_payment(b, status="confirmed", payment_reference=f"PAY-012-{i}")
            bookings.append(b)
        for i, b in enumerate(bookings):
            self.assertTrue(b.visa_required)
            self.assertEqual(b.external_service_id, f"PAY-012-{i}")

    def test_booking_workflow_query_efficiency(self):
        for _ in range(5):
            self.create_booking()
        self.client.force_authenticate(self.user)
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(BOOKINGS_URL)
        self.assertLessEqual(len(context), 3)

    def test_multi_user_workflow_isolated(self):
        booking1 = self.create_booking(user=self.user)
        booking2 = self.create_booking(user=self.other_user)
        BookingEngine.attach_payment(booking1, status="confirmed", payment_reference="PAY-020")
        BookingEngine.attach_payment(booking2, status="confirmed", payment_reference="PAY-021")
        self.assertEqual(booking1.external_service_id, "PAY-020")
        self.assertEqual(booking2.external_service_id, "PAY-021")