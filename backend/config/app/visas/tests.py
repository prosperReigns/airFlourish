from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from app.bookings.models import Booking
from app.flights.models import FlightBooking
from app.payments.models import Payment
from app.services.booking_engine import BookingEngine
from app.visas.models import VisaApplication
from app.visas.serializers import VisaApplicationSerializer

VISAS_URL = "/api/visas/visas/"
VISA_APPROVAL_URL = "/api/visas/approve/"


def throttled_settings(rate):
    rates = dict(settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}))
    rates.update({"anon": rate, "user": rate, "ip": rate})
    return {**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": rates}


class BaseVisaTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="visauser@example.com",
            password="password123",
            country="NG",
        )
        self.other_user = User.objects.create_user(
            email="visaother@example.com",
            password="password123",
            country="NG",
        )
        self.admin = User.objects.create_user(
            email="visaadmin@example.com",
            password="password123",
            country="NG",
            user_type="admin",
            is_staff=True,
        )

    def create_booking(self, user=None, service_type="visa", total_price=Decimal("150.00")):
        return BookingEngine.create_booking(
            user=user or self.user,
            service_type=service_type,
            total_price=total_price,
            currency="NGN",
        )

    def create_flight_booking(self, user=None, arrival_city="France"):
        booking = self.create_booking(user=user or self.user, service_type="flight")
        return FlightBooking.objects.create(
            booking=booking,
            departure_city="Lagos",
            arrival_city=arrival_city,
            departure_date=date(2026, 4, 1),
            return_date=date(2026, 4, 10),
            airline="Test Airline",
            passengers=1,
        )

    def create_payment(self, booking=None, status="successful"):
        booking = booking or self.create_booking(service_type="flight")
        return Payment.objects.create(
            booking=booking,
            amount=Decimal("200.00"),
            currency="NGN",
            payment_method="card",
            tx_ref=f"tx-{booking.id}",
            status=status,
        )

    def create_visa(self, user=None, flight=None, status="pending"):
        booking = self.create_booking(user=user or self.user)
        return VisaApplication.objects.create(
            booking=booking,
            flight=flight,
            destination_country="France",
            visa_type="tourist",
            appointment_date=date(2026, 4, 15),
            status=status,
        )


class VisaFlowTests(BaseVisaTestCase):
    def test_create_requires_auth(self):
        response = self.client.post(VISAS_URL, data={})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_can_create_visa_without_flight(self):
        self.client.force_authenticate(self.user)
        payload = {
            "destination_country": "France",
            "visa_type": "tourist",
            "appointment_date": "2026-04-15",
            "visa_fee": "150.00",
            "currency": "NGN",
        }
        response = self.client.post(VISAS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        visa = VisaApplication.objects.first()
        self.assertIsNone(visa.flight)
        booking = Booking.objects.get(id=visa.booking_id)
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.service_type, "visa")
        self.assertEqual(booking.total_price, Decimal("150.00"))

    def test_create_creates_booking_with_fee_and_currency(self):
        self.client.force_authenticate(self.user)
        payload = {
            "destination_country": "Italy",
            "visa_type": "business",
            "appointment_date": "2026-05-01",
            "visa_fee": "250.00",
            "currency": "USD",
        }
        response = self.client.post(VISAS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        visa = VisaApplication.objects.get(id=response.data["id"])
        self.assertEqual(visa.booking.total_price, Decimal("250.00"))
        self.assertEqual(visa.booking.currency, "USD")

    def test_create_defaults_currency_when_missing(self):
        self.client.force_authenticate(self.user)
        payload = {
            "destination_country": "Spain",
            "visa_type": "tourist",
            "appointment_date": "2026-06-01",
            "visa_fee": "100.00",
        }
        response = self.client.post(VISAS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        visa = VisaApplication.objects.get(id=response.data["id"])
        self.assertEqual(visa.booking.currency, "NGN")

    def test_create_accepts_optional_documents(self):
        self.client.force_authenticate(self.user)
        payload = {
            "destination_country": "Germany",
            "visa_type": "tourist",
            "appointment_date": "2026-06-05",
            "visa_fee": "180.00",
            "currency": "NGN",
            "passport_scan": "passport-data",
            "photo": "photo-data",
            "supporting_docs": "docs-data",
        }
        response = self.client.post(VISAS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        visa = VisaApplication.objects.get(id=response.data["id"])
        self.assertEqual(visa.passport_scan, "passport-data")
        self.assertEqual(visa.photo, "photo-data")
        self.assertEqual(visa.supporting_docs, "docs-data")


class VisaApplicationModelTests(BaseVisaTestCase):
    def test_visa_application_defaults(self):
        visa = VisaApplication.objects.create(
            booking=self.create_booking(),
            destination_country="France",
            visa_type="tourist",
            appointment_date=date(2026, 4, 15),
        )
        self.assertEqual(visa.status, "pending")
        self.assertEqual(visa.document_status, "pending")
        self.assertIsNone(visa.flight)

    def test_visa_application_str_includes_destination_and_type(self):
        visa = self.create_visa()
        visa_string = str(visa)
        self.assertIn("France", visa_string)
        self.assertIn("tourist", visa_string)

    def test_visa_application_allows_null_flight(self):
        visa = self.create_visa(flight=None)
        self.assertIsNone(visa.flight)

    def test_visa_application_accepts_status_choice(self):
        visa = self.create_visa(status="verified")
        self.assertEqual(visa.status, "verified")


class VisaApplicationSerializerTests(BaseVisaTestCase):
    def setUp(self):
        super().setUp()
        self.visa = self.create_visa()

    def test_visa_application_serializer_outputs_expected_fields(self):
        data = VisaApplicationSerializer(self.visa).data
        self.assertEqual(data["booking"], self.visa.booking.id)
        self.assertEqual(data["destination_country"], "France")
        self.assertEqual(data["visa_type"], "tourist")
        self.assertEqual(data["status"], "pending")

    def test_visa_application_serializer_read_only_fields_ignored(self):
        serializer = VisaApplicationSerializer(
            data={
                "booking": self.visa.booking.id,
                "destination_country": "France",
                "visa_type": "tourist",
                "appointment_date": "2026-04-15",
                "document_status": "approved",
            }
        )
        self.assertTrue(serializer.is_valid())
        self.assertNotIn("booking", serializer.validated_data)
        self.assertNotIn("document_status", serializer.validated_data)


class VisaApplicationSerializerValidationTests(TestCase):
    def test_visa_application_serializer_missing_required_fields(self):
        serializer = VisaApplicationSerializer(
            data={
                "visa_type": "tourist",
                "appointment_date": "2026-04-15",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("destination_country", serializer.errors)

    def test_visa_application_serializer_missing_visa_type(self):
        serializer = VisaApplicationSerializer(
            data={
                "destination_country": "France",
                "appointment_date": "2026-04-15",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("visa_type", serializer.errors)

    def test_visa_application_serializer_invalid_date(self):
        serializer = VisaApplicationSerializer(
            data={
                "destination_country": "France",
                "visa_type": "tourist",
                "appointment_date": "not-a-date",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("appointment_date", serializer.errors)

    def test_visa_application_serializer_allows_null_appointment_date(self):
        serializer = VisaApplicationSerializer(
            data={
                "destination_country": "France",
                "visa_type": "tourist",
                "appointment_date": None,
            }
        )
        self.assertTrue(serializer.is_valid())


class VisaApplicationAuthTests(BaseVisaTestCase):
    def test_list_requires_auth(self):
        response = self.client.get(VISAS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_requires_auth(self):
        visa = self.create_visa()
        response = self.client.get(f"{VISAS_URL}{visa.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_requires_auth(self):
        visa = self.create_visa()
        response = self.client.delete(f"{VISAS_URL}{visa.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_requires_auth(self):
        visa = self.create_visa()
        response = self.client.patch(
            f"{VISAS_URL}{visa.id}/",
            data={"visa_type": "business"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class VisaApplicationListRetrieveTests(BaseVisaTestCase):
    def setUp(self):
        super().setUp()
        self.user_visa = self.create_visa(user=self.user)
        self.other_visa = self.create_visa(user=self.other_user)

    def test_regular_user_sees_only_own_visas(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(VISAS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.user_visa.id)

    def test_admin_sees_all_visas(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(VISAS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_user_cannot_retrieve_other_visa(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{VISAS_URL}{self.other_visa.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_retrieve_other_visa(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(f"{VISAS_URL}{self.other_visa.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class VisaApplicationUpdateDeleteTests(BaseVisaTestCase):
    def test_user_can_update_own_visa(self):
        visa = self.create_visa(user=self.user)
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            f"{VISAS_URL}{visa.id}/",
            data={"visa_type": "business"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        visa.refresh_from_db()
        self.assertEqual(visa.visa_type, "business")

    def test_user_cannot_update_other_visa(self):
        visa = self.create_visa(user=self.other_user)
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            f"{VISAS_URL}{visa.id}/",
            data={"visa_type": "business"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_delete_own_visa(self):
        visa = self.create_visa(user=self.user)
        self.client.force_authenticate(self.user)
        response = self.client.delete(f"{VISAS_URL}{visa.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(VisaApplication.objects.filter(id=visa.id).exists())

    def test_user_cannot_delete_other_visa(self):
        visa = self.create_visa(user=self.other_user)
        self.client.force_authenticate(self.user)
        response = self.client.delete(f"{VISAS_URL}{visa.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class VisaApplicationFlightTests(BaseVisaTestCase):
    def test_create_with_flight_not_owned_returns_404(self):
        flight = self.create_flight_booking(user=self.other_user)
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VISAS_URL,
            data={
                "flight_id": flight.id,
                "destination_country": "France",
                "visa_type": "tourist",
                "appointment_date": "2026-04-15",
                "visa_fee": "150.00",
                "currency": "NGN",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_with_flight_destination_mismatch(self):
        flight = self.create_flight_booking(user=self.user, arrival_city="Italy")
        self.create_payment(booking=flight.booking, status="successful")
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VISAS_URL,
            data={
                "flight_id": flight.id,
                "destination_country": "France",
                "visa_type": "tourist",
                "appointment_date": "2026-04-15",
                "visa_fee": "150.00",
                "currency": "NGN",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_flight_unpaid_rejected(self):
        flight = self.create_flight_booking(user=self.user, arrival_city="France")
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VISAS_URL,
            data={
                "flight_id": flight.id,
                "destination_country": "France",
                "visa_type": "tourist",
                "appointment_date": "2026-04-15",
                "visa_fee": "150.00",
                "currency": "NGN",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Flight must be paid before visa application")

    def test_create_with_flight_existing_visa_rejected(self):
        flight = self.create_flight_booking(user=self.user, arrival_city="France")
        self.create_payment(booking=flight.booking, status="successful")
        self.create_visa(user=self.user, flight=flight)
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VISAS_URL,
            data={
                "flight_id": flight.id,
                "destination_country": "France",
                "visa_type": "tourist",
                "appointment_date": "2026-04-15",
                "visa_fee": "150.00",
                "currency": "NGN",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "A visa application already exists for this flight")

    def test_create_with_flight_paid_and_matched_creates_visa(self):
        flight = self.create_flight_booking(user=self.user, arrival_city="France")
        self.create_payment(booking=flight.booking, status="successful")
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VISAS_URL,
            data={
                "flight_id": flight.id,
                "destination_country": "France",
                "visa_type": "tourist",
                "appointment_date": "2026-04-15",
                "visa_fee": "150.00",
                "currency": "NGN",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        visa = VisaApplication.objects.get(id=response.data["id"])
        self.assertEqual(visa.flight_id, flight.id)

    def test_create_with_flight_sets_booking_external_service_id(self):
        flight = self.create_flight_booking(user=self.user, arrival_city="France")
        self.create_payment(booking=flight.booking, status="successful")
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VISAS_URL,
            data={
                "flight_id": flight.id,
                "destination_country": "France",
                "visa_type": "tourist",
                "appointment_date": "2026-04-15",
                "visa_fee": "150.00",
                "currency": "NGN",
                "visa_id": "EXT-123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        visa = VisaApplication.objects.get(id=response.data["id"])
        self.assertEqual(visa.booking.external_service_id, "EXT-123")


class VisaApplicationAdminActionTests(BaseVisaTestCase):
    def test_verify_documents_requires_admin(self):
        visa = self.create_visa(user=self.user)
        self.client.force_authenticate(self.user)
        response = self.client.post(f"{VISAS_URL}{visa.id}/verify_documents/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_verify_documents_admin_sets_status_verified(self):
        visa = self.create_visa(user=self.user)
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"{VISAS_URL}{visa.id}/verify_documents/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        visa.refresh_from_db()
        self.assertEqual(visa.status, "verified")

    def test_approve_action_requires_admin(self):
        visa = self.create_visa(user=self.user)
        self.client.force_authenticate(self.user)
        response = self.client.post(f"{VISAS_URL}{visa.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_approve_action_admin_sets_document_status(self):
        visa = self.create_visa(user=self.user)
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"{VISAS_URL}{visa.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        visa.refresh_from_db()
        self.assertEqual(visa.document_status, "approved")

    def test_reject_action_requires_admin(self):
        visa = self.create_visa(user=self.user)
        self.client.force_authenticate(self.user)
        response = self.client.post(f"{VISAS_URL}{visa.id}/reject/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reject_action_admin_sets_document_status(self):
        visa = self.create_visa(user=self.user)
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"{VISAS_URL}{visa.id}/reject/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        visa.refresh_from_db()
        self.assertEqual(visa.document_status, "rejected")


class VisaApprovalViewTests(BaseVisaTestCase):
    def test_visa_approval_requires_admin(self):
        visa = self.create_visa(user=self.user)
        self.client.force_authenticate(self.user)
        response = self.client.post(
            f"{VISA_APPROVAL_URL}{visa.id}/",
            data={"action": "approve"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_visa_approval_invalid_action(self):
        visa = self.create_visa(user=self.user)
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"{VISA_APPROVAL_URL}{visa.id}/",
            data={"action": "invalid"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_visa_approval_approve_sets_status_and_timestamps(self):
        visa = self.create_visa(user=self.user)
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"{VISA_APPROVAL_URL}{visa.id}/",
            data={"action": "approve"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        visa.refresh_from_db()
        self.assertEqual(visa.status, "approved")
        self.assertIsNotNone(visa.reviewed_at)
        self.assertIsNotNone(visa.approved_at)

    def test_visa_approval_reject_sets_status_and_timestamps(self):
        visa = self.create_visa(user=self.user)
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"{VISA_APPROVAL_URL}{visa.id}/",
            data={"action": "reject"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        visa.refresh_from_db()
        self.assertEqual(visa.status, "rejected")
        self.assertIsNotNone(visa.reviewed_at)
        self.assertIsNotNone(visa.rejected_at)

    def test_visa_approval_not_found_returns_404(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"{VISA_APPROVAL_URL}99999/",
            data={"action": "approve"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class VisaThrottleTests(BaseVisaTestCase):
    @override_settings(REST_FRAMEWORK=throttled_settings("1/minute"))
    def test_throttle_blocks_repeated_list_requests(self):
        self.create_visa()
        self.client.force_authenticate(self.user)
        first = self.client.get(VISAS_URL)
        second = self.client.get(VISAS_URL)
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @override_settings(REST_FRAMEWORK=throttled_settings("1/minute"))
    def test_throttle_blocks_repeated_create_requests(self):
        self.client.force_authenticate(self.user)
        first = self.client.post(
            VISAS_URL,
            data={
                "destination_country": "France",
                "visa_type": "tourist",
                "appointment_date": "2026-04-15",
                "visa_fee": "150.00",
                "currency": "NGN",
            },
            format="json",
        )
        second = self.client.post(
            VISAS_URL,
            data={
                "destination_country": "Italy",
                "visa_type": "business",
                "appointment_date": "2026-05-15",
                "visa_fee": "200.00",
                "currency": "NGN",
            },
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class VisaCachingTests(BaseVisaTestCase):
    def test_cache_store_and_retrieve_visa_list(self):
        visa = self.create_visa()
        data = VisaApplicationSerializer([visa], many=True).data
        cache_key = f"visa_list:{self.user.id}"
        cache.set(cache_key, data, timeout=60)
        cached = cache.get(cache_key)
        self.assertEqual(cached, data)

    def test_cache_clear_removes_cached_entries(self):
        cache_key = f"visa_list:{self.user.id}"
        cache.set(cache_key, ["data"], timeout=60)
        cache.clear()
        self.assertIsNone(cache.get(cache_key))


class VisaPerformanceTests(BaseVisaTestCase):
    def test_list_query_count_is_small(self):
        self.create_visa()
        self.client.force_authenticate(self.user)
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(VISAS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(context), 3)

    def test_retrieve_query_count_is_small(self):
        visa = self.create_visa()
        self.client.force_authenticate(self.user)
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(f"{VISAS_URL}{visa.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(context), 3)
class VisaExtraTests(BaseVisaTestCase):

    # -------------------------
    # Visa Creation Edge Cases
    # -------------------------
    def test_create_with_empty_payload(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(VISAS_URL, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_invalid_fee_type(self):
        self.client.force_authenticate(self.user)
        payload = {
            "destination_country": "France",
            "visa_type": "tourist",
            "appointment_date": "2026-04-15",
            "visa_fee": "abc",
            "currency": "NGN",
        }
        response = self.client.post(VISAS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_past_appointment_date(self):
        self.client.force_authenticate(self.user)
        past_date = (date.today() - timedelta(days=10)).isoformat()
        payload = {
            "destination_country": "France",
            "visa_type": "tourist",
            "appointment_date": past_date,
            "visa_fee": "150.00",
            "currency": "NGN",
        }
        response = self.client.post(VISAS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_large_fee(self):
        self.client.force_authenticate(self.user)
        payload = {
            "destination_country": "France",
            "visa_type": "business",
            "appointment_date": "2026-04-15",
            "visa_fee": "1000000.00",
            "currency": "NGN",
        }
        response = self.client.post(VISAS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        visa = VisaApplication.objects.get(id=response.data["id"])
        self.assertEqual(visa.booking.total_price, Decimal("1000000.00"))

    def test_create_with_missing_optional_fields(self):
        self.client.force_authenticate(self.user)
        payload = {
            "destination_country": "France",
            "visa_type": "tourist",
            "appointment_date": "2026-04-15",
            "visa_fee": "150.00",
        }
        response = self.client.post(VISAS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # -------------------------
    # Flight-Related Edge Cases
    # -------------------------
    def test_create_with_flight_departure_after_appointment(self):
        flight = self.create_flight_booking(user=self.user, arrival_city="France")
        self.create_payment(booking=flight.booking, status="successful")
        self.client.force_authenticate(self.user)
        payload = {
            "flight_id": flight.id,
            "destination_country": "France",
            "visa_type": "tourist",
            "appointment_date": "2026-03-01",  # before flight
            "visa_fee": "150.00",
            "currency": "NGN",
        }
        response = self.client.post(VISAS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_nonexistent_flight(self):
        self.client.force_authenticate(self.user)
        payload = {
            "flight_id": 99999,
            "destination_country": "France",
            "visa_type": "tourist",
            "appointment_date": "2026-04-15",
            "visa_fee": "150.00",
            "currency": "NGN",
        }
        response = self.client.post(VISAS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_with_multiple_visas_on_same_flight(self):
        flight = self.create_flight_booking(user=self.user, arrival_city="France")
        self.create_payment(booking=flight.booking, status="successful")
        self.create_visa(user=self.user, flight=flight)
        self.client.force_authenticate(self.user)
        payload = {
            "flight_id": flight.id,
            "destination_country": "France",
            "visa_type": "tourist",
            "appointment_date": "2026-04-15",
            "visa_fee": "150.00",
            "currency": "NGN",
        }
        response = self.client.post(VISAS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------
    # Authorization / Admin
    # -------------------------
    def test_non_admin_cannot_change_document_status(self):
        visa = self.create_visa(user=self.user)
        self.client.force_authenticate(self.user)
        response = self.client.post(f"{VISA_APPROVAL_URL}{visa.id}/", {"action": "approve"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_approve_and_reject_multiple_visas(self):
        visas = [self.create_visa(user=self.user) for _ in range(3)]
        self.client.force_authenticate(self.admin)
        for visa in visas:
            response = self.client.post(f"{VISA_APPROVAL_URL}{visa.id}/", {"action": "approve"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            visa.refresh_from_db()
            self.assertEqual(visa.status, "approved")
            response = self.client.post(f"{VISA_APPROVAL_URL}{visa.id}/", {"action": "reject"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            visa.refresh_from_db()
            self.assertEqual(visa.status, "rejected")

    # -------------------------
    # Serializer Validations
    # -------------------------
    def test_serializer_ignores_extra_fields(self):
        serializer = VisaApplicationSerializer(
            data={
                "destination_country": "France",
                "visa_type": "tourist",
                "appointment_date": "2026-04-15",
                "extra_field": "ignored",
            }
        )
        self.assertTrue(serializer.is_valid())

    def test_serializer_rejects_invalid_field_types(self):
        serializer = VisaApplicationSerializer(
            data={
                "destination_country": 123,
                "visa_type": 456,
                "appointment_date": "not-a-date",
            }
        )
        self.assertFalse(serializer.is_valid())

    # -------------------------
    # Caching
    # -------------------------
    def test_cache_invalidated_after_visa_update(self):
        visa = self.create_visa()
        cache_key = f"visa_list:{self.user.id}"
        cache.set(cache_key, ["dummy"], timeout=60)
        self.client.force_authenticate(self.user)
        self.client.patch(f"{VISAS_URL}{visa.id}/", {"visa_type": "business"}, format="json")
        self.assertIsNone(cache.get(cache_key))

    def test_cache_invalidated_after_delete(self):
        visa = self.create_visa()
        cache_key = f"visa_list:{self.user.id}"
        cache.set(cache_key, ["dummy"], timeout=60)
        self.client.force_authenticate(self.user)
        self.client.delete(f"{VISAS_URL}{visa.id}/")
        self.assertIsNone(cache.get(cache_key))

    # -------------------------
    # Throttling / Rate Limit
    # -------------------------
    @override_settings(REST_FRAMEWORK=throttled_settings("1/minute"))
    def test_throttle_separate_users(self):
        self.create_visa()
        other_user = self.other_user
        self.client.force_authenticate(self.user)
        self.client.get(VISAS_URL)
        self.client.force_authenticate(other_user)
        response = self.client.get(VISAS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # -------------------------
    # Performance
    # -------------------------
    def test_list_query_count_small_for_many_visas(self):
        for _ in range(10):
            self.create_visa()
        self.client.force_authenticate(self.user)
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(VISAS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(ctx), 5)

    # -------------------------
    # Misc Edge Cases
    # -------------------------
    def test_str_method_handles_null_fields(self):
        visa = self.create_visa(flight=None)
        s = str(visa)
        self.assertIn("France", s)
        self.assertIn("tourist", s)

    def test_multiple_visa_types_for_user(self):
        self.create_visa(user=self.user)
        self.create_visa(user=self.user, status="verified")
        self.client.force_authenticate(self.user)
        response = self.client.get(VISAS_URL)
        self.assertEqual(len(response.data), 2)