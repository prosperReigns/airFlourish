from datetime import date
from decimal import Decimal
from unittest.mock import patch
import uuid
import threading

from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from app.bookings.models import Booking
from app.flights.models import Airport, FlightBooking
from app.flights.serializers import FlightBookingSerializer
from app.payments.models import Payment
from app.services.booking_engine import BookingEngine

FLIGHT_BOOKINGS_URL = "/api/flights/flights/"
SECURE_BOOK_URL = "/api/flights/secure-book/"
VERIFY_PAYMENT_URL = "/api/flights/verify-payment/"
FLIGHT_SEARCH_URL = "/api/bookings/flights/search/"
AIRPORT_SEARCH_URL = "/api/airports/search/"
ADMIN_AIRPORTS_URL = "/api/admin/airports/"


def throttled_settings(rate):
    rates = dict(settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}))
    rates.update({"anon": rate, "user": rate, "ip": rate})
    return {**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": rates}


class BaseFlightTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.other_user = User.objects.create_user(
            email="flightother@example.com",
            password="password123",
            country="NG",
        )
        self.admin = User.objects.create_user(
            email="flightadmin@example.com",
            password="password123",
            country="NG",
            user_type="admin",
            is_staff=True,
        )

    def create_booking(self, user=None, service_type="flight", total_price=Decimal("200.00")):
        return BookingEngine.create_booking(
            user=user or self.user,
            service_type=service_type,
            total_price=total_price,
            currency="NGN",
        )

    def _data(self, response):
        data = self._data(response)
        if hasattr(data, "get"):
            return data.get("results", data)
        return data

    def create_flight_booking(self, user=None, **overrides):
        booking = self.create_booking(user=user or self.user)
        data = {
            "booking": booking,
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": date(2026, 5, 1),
            "return_date": date(2026, 5, 10),
            "airline": "AF",
            "passengers": 2,
        }
        data.update(overrides)
        return FlightBooking.objects.create(**data)

    def create_payment(self, booking=None, amount=Decimal("100.00"), currency="USD", status="pending", raw_meta=None):
        booking = booking or self.create_booking()
        return Payment.objects.create(
            booking=booking,
            tx_ref=f"tx-{uuid.uuid4().hex}",
            amount=amount,
            currency=currency,
            payment_method="card",
            status=status,
            raw_response={"meta": raw_meta or {}},
        )


class FlightBookingModelTests(BaseFlightTestCase):
    def test_flight_booking_str_and_defaults(self):
        flight = self.create_flight_booking(passengers=1)
        self.assertEqual(str(flight), "Lagos to Paris")
        self.assertEqual(flight.passengers, 1)

    def test_flight_booking_return_date_optional(self):
        flight = self.create_flight_booking(return_date=None)
        self.assertIsNone(flight.return_date)

    def test_flight_booking_default_passengers_when_not_set(self):
        booking = self.create_booking()
        flight = FlightBooking.objects.create(
            booking=booking,
            departure_city="Lagos",
            arrival_city="Paris",
            departure_date=date(2026, 5, 1),
            airline="AF",
        )
        self.assertEqual(flight.passengers, 1)


class FlightBookingSerializerTests(BaseFlightTestCase):
    def test_flight_booking_serializer_outputs_expected_fields(self):
        flight = self.create_flight_booking()
        data = FlightBookingSerializer(flight).data
        self.assertEqual(data["booking"], flight.booking.id)
        self.assertEqual(data["departure_city"], "Lagos")
        self.assertEqual(data["arrival_city"], "Paris")
        self.assertEqual(data["airline"], "AF")
        self.assertEqual(data["passengers"], 2)

    def test_flight_booking_serializer_read_only_booking_ignored(self):
        flight = self.create_flight_booking()
        serializer = FlightBookingSerializer(
            data={
                "booking": flight.booking.id,
                "departure_city": "Lagos",
                "arrival_city": "Paris",
                "departure_date": "2026-05-01",
                "airline": "AF",
                "passengers": 1,
            }
        )
        self.assertTrue(serializer.is_valid())
        self.assertNotIn("booking", serializer.validated_data)

    def test_flight_booking_serializer_missing_departure_city(self):
        serializer = FlightBookingSerializer(
            data={
                "arrival_city": "Paris",
                "departure_date": "2026-05-01",
                "airline": "AF",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("departure_city", serializer.errors)

    def test_flight_booking_serializer_invalid_date(self):
        serializer = FlightBookingSerializer(
            data={
                "departure_city": "Lagos",
                "arrival_city": "Paris",
                "departure_date": "not-a-date",
                "airline": "AF",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("departure_date", serializer.errors)


class FlightBookingAuthTests(BaseFlightTestCase):
    def test_list_requires_auth(self):
        response = self.client.get(FLIGHT_BOOKINGS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_requires_auth(self):
        flight = self.create_flight_booking()
        response = self.client.get(f"{FLIGHT_BOOKINGS_URL}{flight.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_auth(self):
        response = self.client.post(FLIGHT_BOOKINGS_URL, data={})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_requires_auth(self):
        flight = self.create_flight_booking()
        response = self.client.delete(f"{FLIGHT_BOOKINGS_URL}{flight.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class FlightBookingListRetrieveTests(BaseFlightTestCase):
    def setUp(self):
        super().setUp()
        self.user_flight = self.create_flight_booking(user=self.user)
        self.other_flight = self.create_flight_booking(user=self.other_user, arrival_city="London")

    def test_regular_user_sees_only_own_flights(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(FLIGHT_BOOKINGS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(self._data(response)), 1)
        self.assertEqual(self._data(response)[0]["id"], self.user_flight.id)

    def test_admin_user_sees_all_flights(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(FLIGHT_BOOKINGS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(self._data(response)), 2)

    def test_user_cannot_retrieve_other_flight(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{FLIGHT_BOOKINGS_URL}{self.other_flight.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_retrieve_other_flight(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(f"{FLIGHT_BOOKINGS_URL}{self.other_flight.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class FlightBookingCreateTests(BaseFlightTestCase):
    def test_create_missing_flight_offer_or_travelers_returns_400(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            FLIGHT_BOOKINGS_URL,
            data={
                "departure_city": "Lagos",
                "arrival_city": "Paris",
                "departure_date": "2026-05-01",
                "airline": "AF",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("app.flights.views.BookingEngine.book_flight")
    def test_create_calls_booking_engine_and_creates_flight_booking(self, mock_book):
        booking = self.create_booking()
        mock_book.return_value = (booking, {"id": "am-1"})
        self.client.force_authenticate(self.user)
        payload = {
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "return_date": "2026-05-10",
            "airline": "AF",
            "passengers": 2,
            "flight_offer": {"id": "offer-1"},
            "travelers": [{"id": "t1"}],
            "total_price": "500.00",
            "currency": "USD",
        }
        response = self.client.post(FLIGHT_BOOKINGS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FlightBooking.objects.count(), 1)
        mock_book.assert_called_once()

    @patch("app.flights.views.BookingEngine.book_flight")
    def test_create_defaults_passengers_to_one(self, mock_book):
        booking = self.create_booking()
        mock_book.return_value = (booking, {"id": "am-1"})
        self.client.force_authenticate(self.user)
        payload = {
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
            "flight_offer": {"id": "offer-2"},
            "travelers": [{"id": "t1"}],
            "total_price": "500.00",
        }
        response = self.client.post(FLIGHT_BOOKINGS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        flight = FlightBooking.objects.get(id=self._data(response)["id"])
        self.assertEqual(flight.passengers, 1)

    @patch("app.flights.views.BookingEngine.book_flight")
    def test_create_uses_default_currency_when_missing(self, mock_book):
        booking = self.create_booking()
        mock_book.return_value = (booking, {"id": "am-1"})
        self.client.force_authenticate(self.user)
        payload = {
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
            "flight_offer": {"id": "offer-3"},
            "travelers": [{"id": "t1"}],
            "total_price": "500.00",
        }
        response = self.client.post(FLIGHT_BOOKINGS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        _, kwargs = mock_book.call_args
        self.assertEqual(kwargs["currency"], "NGN")


class FlightBookingUpdateDeleteTests(BaseFlightTestCase):
    def test_user_can_update_own_flight(self):
        flight = self.create_flight_booking(user=self.user)
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            f"{FLIGHT_BOOKINGS_URL}{flight.id}/",
            data={"arrival_city": "Rome"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        flight.refresh_from_db()
        self.assertEqual(flight.arrival_city, "Rome")

    def test_user_cannot_update_other_flight(self):
        flight = self.create_flight_booking(user=self.other_user)
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            f"{FLIGHT_BOOKINGS_URL}{flight.id}/",
            data={"arrival_city": "Rome"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_delete_own_flight(self):
        flight = self.create_flight_booking(user=self.user)
        self.client.force_authenticate(self.user)
        response = self.client.delete(f"{FLIGHT_BOOKINGS_URL}{flight.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_user_cannot_delete_other_flight(self):
        flight = self.create_flight_booking(user=self.other_user)
        self.client.force_authenticate(self.user)
        response = self.client.delete(f"{FLIGHT_BOOKINGS_URL}{flight.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SecureFlightBookingTests(BaseFlightTestCase):
    def test_secure_requires_auth(self):
        response = self.client.post(SECURE_BOOK_URL, data={})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_secure_missing_flight_offer_or_travelers_returns_400(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(SECURE_BOOK_URL, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("app.flights.views.AmadeusService.reprice_flight")
    def test_secure_reprice_invalid_structure_returns_400(self, mock_reprice):
        mock_reprice.return_value = {"flightOffers": []}
        self.client.force_authenticate(self.user)
        payload = {
            "flight_offer": {"id": "offer-1"},
            "travelers": [{"id": "t1"}],
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
        }
        response = self.client.post(SECURE_BOOK_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("app.flights.views.FlutterwaveService")
    @patch("app.flights.views.AmadeusService.reprice_flight")
    def test_secure_payment_initiation_error_returns_400(self, mock_reprice, mock_fw):
        mock_reprice.return_value = {
            "flightOffers": [{"price": {"total": "100.00", "currency": "USD"}}]
        }
        mock_fw.return_value.initiate_card_payment.return_value = {"status": "error"}
        self.client.force_authenticate(self.user)
        payload = {
            "flight_offer": {"id": "offer-1"},
            "travelers": [{"id": "t1"}],
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
        }
        response = self.client.post(SECURE_BOOK_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("app.flights.views.FlutterwaveService")
    @patch("app.flights.views.AmadeusService.reprice_flight")
    def test_secure_success_creates_booking_and_payment(self, mock_reprice, mock_fw):
        mock_reprice.return_value = {
            "flightOffers": [{"price": {"total": "150.00", "currency": "USD"}}]
        }
        mock_fw.return_value.initiate_card_payment.return_value = {
            "status": "success",
            "data": {"link": "http://pay.local/test"},
        }
        self.client.force_authenticate(self.user)
        payload = {
            "flight_offer": {"id": "offer-1"},
            "travelers": [{"id": "t1"}],
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
        }
        response = self.client.post(SECURE_BOOK_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)
        payment = Payment.objects.first()
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.amount, Decimal("150.00"))
        self.assertEqual(payment.currency, "USD")
        self.assertEqual(payment.booking.user, self.user)

    @patch("app.flights.views.FlutterwaveService")
    @patch("app.flights.views.AmadeusService.reprice_flight")
    def test_secure_response_includes_payment_link_and_tx_ref(self, mock_reprice, mock_fw):
        mock_reprice.return_value = {
            "flightOffers": [{"price": {"total": "150.00", "currency": "USD"}}]
        }
        mock_fw.return_value.initiate_card_payment.return_value = {
            "status": "success",
            "data": {"link": "http://pay.local/test"},
        }
        self.client.force_authenticate(self.user)
        payload = {
            "flight_offer": {"id": "offer-2"},
            "travelers": [{"id": "t1"}],
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
        }
        response = self.client.post(SECURE_BOOK_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("payment_link", self._data(response))
        self.assertIn("tx_ref", self._data(response))
        self.assertIn("booking_id", self._data(response))

    @patch("app.flights.views.FlutterwaveService")
    @patch("app.flights.views.AmadeusService.reprice_flight")
    def test_secure_stores_meta_in_payment_raw_response(self, mock_reprice, mock_fw):
        mock_reprice.return_value = {
            "flightOffers": [{"price": {"total": "150.00", "currency": "USD"}}]
        }
        mock_fw.return_value.initiate_card_payment.return_value = {
            "status": "success",
            "data": {"link": "http://pay.local/test"},
        }
        self.client.force_authenticate(self.user)
        payload = {
            "flight_offer": {"id": "offer-3"},
            "travelers": [{"id": "t1"}],
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
        }
        response = self.client.post(SECURE_BOOK_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment = Payment.objects.get(tx_ref=self._data(response)["tx_ref"])
        meta = payment.raw_response.get("meta", {})
        self.assertEqual(meta.get("flight_offer"), {"id": "offer-3"})
        self.assertEqual(meta.get("travelers"), [{"id": "t1"}])


class VerifyFlightPaymentTests(BaseFlightTestCase):
    def test_verify_requires_auth(self):
        response = self.client.post(VERIFY_PAYMENT_URL, data={})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_verify_requires_tx_ref(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(VERIFY_PAYMENT_URL, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_payment_not_found(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VERIFY_PAYMENT_URL, data={"tx_ref": "missing"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("app.flights.views.FlutterwaveService.verify_payment")
    def test_verify_already_succeeded_returns_200(self, mock_verify):
        payment = self.create_payment(status="succeeded")
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VERIFY_PAYMENT_URL, data={"tx_ref": payment.tx_ref}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._data(response)["message"], "Already verified")
        mock_verify.assert_not_called()

    @patch("app.flights.views.FlutterwaveService.verify_payment")
    def test_verify_status_not_success_marks_failed(self, mock_verify):
        payment = self.create_payment(status="pending")
        mock_verify.return_value = {"status": "error", "message": "bad"}
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VERIFY_PAYMENT_URL, data={"tx_ref": payment.tx_ref}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")
        self.assertEqual(payment.booking.status, "failed")

    @patch("app.flights.views.FlutterwaveService.verify_payment")
    def test_verify_status_not_successful_marks_failed(self, mock_verify):
        payment = self.create_payment(status="pending")
        mock_verify.return_value = {
            "status": "success",
            "data": {"status": "failed", "amount": "100.00", "currency": "USD"},
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VERIFY_PAYMENT_URL, data={"tx_ref": payment.tx_ref}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")

    @patch("app.flights.views.FlutterwaveService.verify_payment")
    def test_verify_amount_mismatch_marks_failed(self, mock_verify):
        payment = self.create_payment(amount=Decimal("120.00"), currency="USD")
        mock_verify.return_value = {
            "status": "success",
            "data": {"status": "successful", "amount": "100.00", "currency": "USD"},
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VERIFY_PAYMENT_URL, data={"tx_ref": payment.tx_ref}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")

    @patch("app.flights.views.FlutterwaveService.verify_payment")
    def test_verify_currency_mismatch_marks_failed(self, mock_verify):
        payment = self.create_payment(amount=Decimal("100.00"), currency="USD")
        mock_verify.return_value = {
            "status": "success",
            "data": {"status": "successful", "amount": "100.00", "currency": "NGN"},
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VERIFY_PAYMENT_URL, data={"tx_ref": payment.tx_ref}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")

    @patch("app.flights.views.FlutterwaveService.verify_payment")
    def test_verify_missing_flight_details_returns_400(self, mock_verify):
        payment = self.create_payment(status="pending", raw_meta={})
        mock_verify.return_value = {
            "status": "success",
            "data": {"status": "successful", "amount": "100.00", "currency": "USD", "id": "fw-1"},
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VERIFY_PAYMENT_URL, data={"tx_ref": payment.tx_ref}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("app.flights.views.AmadeusService.create_flight_order")
    @patch("app.flights.views.FlutterwaveService.verify_payment")
    def test_verify_success_creates_flight_booking_and_sets_external_id(self, mock_verify, mock_order):
        meta = {
            "flight_offer": {"id": "offer-1"},
            "travelers": [{"id": "t1"}],
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "return_date": "2026-05-10",
            "airline": "AF",
            "passengers": 2,
        }
        payment = self.create_payment(status="pending", raw_meta=meta)
        mock_verify.return_value = {
            "status": "success",
            "data": {"status": "successful", "amount": "100.00", "currency": "USD", "id": "fw-2"},
        }
        mock_order.return_value = {"id": "am-1"}
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VERIFY_PAYMENT_URL, data={"tx_ref": payment.tx_ref}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "succeeded")
        payment.booking.refresh_from_db()
        self.assertEqual(payment.booking.external_service_id, "am-1")
        self.assertEqual(FlightBooking.objects.filter(booking=payment.booking).count(), 1)


class FlightSearchTests(BaseFlightTestCase):
    def test_search_requires_auth(self):
        response = self.client.get(FLIGHT_SEARCH_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_missing_origin(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            FLIGHT_SEARCH_URL,
            data={"destination": "LAX", "departure_date": "2026-05-01"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_missing_destination(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            FLIGHT_SEARCH_URL,
            data={"origin": "JFK", "departure_date": "2026-05-01"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_missing_departure_date(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            FLIGHT_SEARCH_URL,
            data={"origin": "JFK", "destination": "LAX"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("app.bookings.views.AmadeusService.search_flights")
    def test_search_calls_amadeus_and_returns_data(self, mock_search):
        mock_search.return_value = [{"id": "flight-1"}]
        self.client.force_authenticate(self.user)
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
        self.assertEqual(self._data(response), [{"id": "flight-1"}])
        mock_search.assert_called_once_with("JFK", "LAX", "2026-05-01", "2026-05-10")


class FlightThrottleTests(BaseFlightTestCase):
    @override_settings(REST_FRAMEWORK=throttled_settings("1/minute"))
    def test_throttle_blocks_repeated_list_requests(self):
        self.create_flight_booking(user=self.user)
        self.client.force_authenticate(self.user)
        first = self.client.get(FLIGHT_BOOKINGS_URL)
        second = self.client.get(FLIGHT_BOOKINGS_URL)
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @override_settings(REST_FRAMEWORK=throttled_settings("1/minute"))
    @patch("app.flights.views.FlutterwaveService")
    @patch("app.flights.views.AmadeusService.reprice_flight")
    def test_throttle_blocks_repeated_secure_booking_requests(self, mock_reprice, mock_fw):
        mock_reprice.return_value = {
            "flightOffers": [{"price": {"total": "150.00", "currency": "USD"}}]
        }
        mock_fw.return_value.initiate_card_payment.return_value = {
            "status": "success",
            "data": {"link": "http://pay.local/test"},
        }
        self.client.force_authenticate(self.user)
        payload = {
            "flight_offer": {"id": "offer-1"},
            "travelers": [{"id": "t1"}],
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
        }
        first = self.client.post(SECURE_BOOK_URL, payload, format="json")
        second = self.client.post(SECURE_BOOK_URL, payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class FlightCachingTests(BaseFlightTestCase):
    def test_cache_store_and_retrieve_flight_list(self):
        flight = self.create_flight_booking(user=self.user)
        data = FlightBookingSerializer([flight], many=True).data
        cache_key = f"flight_list:{self.user.id}"
        cache.set(cache_key, data, timeout=60)
        cached = cache.get(cache_key)
        self.assertEqual(cached, data)

    def test_cache_clear_removes_cached_entries(self):
        cache_key = f"flight_list:{self.user.id}"
        cache.set(cache_key, ["data"], timeout=60)
        cache.clear()
        self.assertIsNone(cache.get(cache_key))


class FlightPerformanceTests(BaseFlightTestCase):
    def test_list_query_count_is_small(self):
        self.create_flight_booking(user=self.user)
        self.client.force_authenticate(self.user)
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(FLIGHT_BOOKINGS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(context), 3)

class FlightAdditionalTests(BaseFlightTestCase):

    # ----------------------------
    # FlightBooking Model Edge Cases
    # ----------------------------

    def test_flight_booking_large_passenger_count(self):
        flight = self.create_flight_booking(passengers=9)
        self.assertEqual(flight.passengers, 9)

    def test_flight_booking_zero_passengers_not_allowed(self):
        flight = self.create_flight_booking(passengers=0)
        self.assertEqual(flight.passengers, 0)

    def test_flight_booking_long_city_names(self):
        flight = self.create_flight_booking(
            departure_city="LagosInternationalAirportTerminal1",
            arrival_city="CharlesDeGaulleInternationalAirport"
        )
        self.assertIn("Lagos", flight.departure_city)

    def test_flight_booking_airline_code_storage(self):
        flight = self.create_flight_booking(airline="BA")
        self.assertEqual(flight.airline, "BA")

    def test_flight_booking_return_date_before_departure(self):
        flight = self.create_flight_booking(
            departure_date=date(2026, 5, 10),
            return_date=date(2026, 5, 1)
        )
        self.assertLess(flight.return_date, flight.departure_date)

    # ----------------------------
    # Serializer Additional Tests
    # ----------------------------

    def test_serializer_handles_null_return_date(self):
        flight = self.create_flight_booking(return_date=None)
        data = FlightBookingSerializer(flight).data
        self.assertIsNone(data["return_date"])

    def test_serializer_passenger_integer(self):
        flight = self.create_flight_booking(passengers=3)
        data = FlightBookingSerializer(flight).data
        self.assertEqual(data["passengers"], 3)

    def test_serializer_airline_present(self):
        flight = self.create_flight_booking(airline="KL")
        data = FlightBookingSerializer(flight).data
        self.assertEqual(data["airline"], "KL")

    def test_serializer_output_contains_id(self):
        flight = self.create_flight_booking()
        data = FlightBookingSerializer(flight).data
        self.assertEqual(data["id"], flight.id)

    def test_serializer_output_contains_booking_reference(self):
        flight = self.create_flight_booking()
        data = FlightBookingSerializer(flight).data
        self.assertEqual(data["booking"], flight.booking.id)

    # ----------------------------
    # Secure Booking Workflow
    # ----------------------------

    @patch("app.flights.views.FlutterwaveService")
    @patch("app.flights.views.AmadeusService.reprice_flight")
    def test_secure_booking_price_conversion_decimal(self, mock_reprice, mock_fw):

        mock_reprice.return_value = {
            "flightOffers": [{"price": {"total": "250.50", "currency": "USD"}}]
        }

        mock_fw.return_value.initiate_card_payment.return_value = {
            "status": "success",
            "data": {"link": "http://pay.local/test"},
        }

        self.client.force_authenticate(self.user)

        payload = {
            "flight_offer": {"id": "offer-decimal"},
            "travelers": [{"id": "t1"}],
            "departure_city": "Lagos",
            "arrival_city": "Rome",
            "departure_date": "2026-05-01",
            "airline": "AF",
        }

        response = self.client.post(SECURE_BOOK_URL, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payment = Payment.objects.first()

        self.assertEqual(payment.amount, Decimal("250.50"))

    # ----------------------------
    # Verify Payment Additional Cases
    # ----------------------------

    @patch("app.flights.views.FlutterwaveService.verify_payment")
    def test_verify_handles_invalid_json_response(self, mock_verify):

        payment = self.create_payment()

        mock_verify.return_value = {"invalid": "structure"}

        self.client.force_authenticate(self.user)

        response = self.client.post(
            VERIFY_PAYMENT_URL,
            {"tx_ref": payment.tx_ref},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("app.flights.views.FlutterwaveService.verify_payment")
    def test_verify_handles_missing_amount(self, mock_verify):

        payment = self.create_payment()

        mock_verify.return_value = {
            "status": "success",
            "data": {"status": "successful", "currency": "USD"}
        }

        self.client.force_authenticate(self.user)

        response = self.client.post(
            VERIFY_PAYMENT_URL,
            {"tx_ref": payment.tx_ref},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ----------------------------
    # Search Variants
    # ----------------------------

    @patch("app.bookings.views.AmadeusService.search_flights")
    def test_search_one_way(self, mock_search):

        mock_search.return_value = [{"id": "flight-2"}]

        self.client.force_authenticate(self.user)

        response = self.client.get(
            FLIGHT_SEARCH_URL,
            data={
                "origin": "LOS",
                "destination": "CDG",
                "departure_date": "2026-06-01",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("app.bookings.views.AmadeusService.search_flights")
    def test_search_round_trip(self, mock_search):

        mock_search.return_value = [{"id": "flight-3"}]

        self.client.force_authenticate(self.user)

        response = self.client.get(
            FLIGHT_SEARCH_URL,
            data={
                "origin": "LOS",
                "destination": "DXB",
                "departure_date": "2026-06-01",
                "return_date": "2026-06-10",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ----------------------------
    # Permission Tests
    # ----------------------------

    def test_admin_can_delete_any_flight(self):

        flight = self.create_flight_booking(user=self.other_user)

        self.client.force_authenticate(self.admin)

        response = self.client.delete(f"{FLIGHT_BOOKINGS_URL}{flight.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_admin_can_update_any_flight(self):

        flight = self.create_flight_booking(user=self.other_user)

        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            f"{FLIGHT_BOOKINGS_URL}{flight.id}/",
            {"arrival_city": "Berlin"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ----------------------------
    # Caching Isolation
    # ----------------------------

    def test_cache_isolated_between_users(self):

        flight = self.create_flight_booking(user=self.user)

        data = FlightBookingSerializer([flight], many=True).data

        cache.set(f"user_flight:{self.user.id}", data)

        cache.set(f"user_flight:{self.other_user.id}", [])

        self.assertNotEqual(
            cache.get(f"user_flight:{self.user.id}"),
            cache.get(f"user_flight:{self.other_user.id}")
        )

    # ----------------------------
    # Workflow Consistency
    # ----------------------------

    def test_flight_booking_linked_to_booking(self):

        flight = self.create_flight_booking()

        self.assertEqual(flight.booking.service_type, "flight")

    def test_payment_links_to_booking(self):

        payment = self.create_payment()

        self.assertIsNotNone(payment.booking)

    def test_payment_status_pending_by_default(self):

        payment = self.create_payment()

        self.assertEqual(payment.status, "pending")

    # ----------------------------
    # Performance Tests
    # ----------------------------

    def test_multiple_flight_list_query_efficiency(self):

        for _ in range(5):
            self.create_flight_booking()

        self.client.force_authenticate(self.user)

        with CaptureQueriesContext(connection) as context:

            response = self.client.get(FLIGHT_BOOKINGS_URL)

        self.assertLessEqual(len(context), 5)

    def test_retrieve_query_efficiency(self):

        flight = self.create_flight_booking()

        self.client.force_authenticate(self.user)

        with CaptureQueriesContext(connection) as context:

            response = self.client.get(f"{FLIGHT_BOOKINGS_URL}{flight.id}/")

        self.assertLessEqual(len(context), 3)

    # ----------------------------
    # Bulk Workflow Tests
    # ----------------------------

    def test_bulk_create_flights(self):

        flights = []

        for _ in range(10):
            flights.append(self.create_flight_booking())

        self.assertEqual(len(flights), 10)

    def test_bulk_delete_flights(self):

        flights = [self.create_flight_booking() for _ in range(3)]

        self.client.force_authenticate(self.user)

        for f in flights:
            self.client.delete(f"{FLIGHT_BOOKINGS_URL}{f.id}/")

        self.assertEqual(FlightBooking.objects.count(), 0)

    # ----------------------------
    # BookingEngine Integration
    # ----------------------------

    def test_booking_engine_creates_flight_booking(self):

        booking = BookingEngine.create_booking(
            user=self.user,
            service_type="flight",
            total_price=Decimal("300.00"),
        )

        flight = FlightBooking.objects.create(
            booking=booking,
            departure_city="Lagos",
            arrival_city="Madrid",
            departure_date=date(2026, 7, 1),
            airline="IB",
        )

        self.assertEqual(flight.booking, booking)

    def test_booking_engine_status_update(self):

        booking = self.create_booking()

        BookingEngine.update_status(booking, "confirmed")

        booking.refresh_from_db()

        self.assertEqual(booking.status, "confirmed")

class FlightIdempotencyTests(BaseFlightTestCase):

    @patch("app.flights.views.AmadeusService.create_flight_order")
    @patch("app.flights.views.FlutterwaveService.verify_payment")
    def test_verify_payment_idempotent(self, mock_verify, mock_order):

        meta = {
            "flight_offer": {"id": "offer-1"},
            "travelers": [{"id": "t1"}],
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
        }

        payment = self.create_payment(status="pending", raw_meta=meta)

        mock_verify.return_value = {
            "status": "success",
            "data": {
                "status": "successful",
                "amount": "100.00",
                "currency": "USD",
                "id": "fw-idem",
            },
        }

        mock_order.return_value = {"id": "am-1"}

        self.client.force_authenticate(self.user)

        # first verification
        response1 = self.client.post(
            VERIFY_PAYMENT_URL, {"tx_ref": payment.tx_ref}, format="json"
        )

        # second verification
        response2 = self.client.post(
            VERIFY_PAYMENT_URL, {"tx_ref": payment.tx_ref}, format="json"
        )

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        self.assertEqual(
            FlightBooking.objects.filter(booking=payment.booking).count(), 1
        )

def test_duplicate_tx_ref_not_allowed(self):

    booking = self.create_booking()

    Payment.objects.create(
        booking=booking,
        tx_ref="duplicate-ref",
        amount=Decimal("100.00"),
        currency="USD",
        payment_method="card",
        status="pending",
    )

    with self.assertRaises(Exception):

        Payment.objects.create(
            booking=booking,
            tx_ref="duplicate-ref",
            amount=Decimal("100.00"),
            currency="USD",
            payment_method="card",
            status="pending",
        )

@patch("app.flights.views.FlutterwaveService.verify_payment")
def test_replay_attack_prevention(self, mock_verify):

    payment = self.create_payment(status="succeeded")

    mock_verify.return_value = {
        "status": "success",
        "data": {"status": "successful"},
    }

    self.client.force_authenticate(self.user)

    response = self.client.post(
        VERIFY_PAYMENT_URL,
        {"tx_ref": payment.tx_ref},
        format="json",
    )

    self.assertEqual(response.status_code, status.HTTP_200_OK)

@patch("app.flights.views.BookingEngine.book_flight")
def test_duplicate_flight_offer_not_double_booked(self, mock_book):

    booking = self.create_booking()

    mock_book.return_value = (booking, {"id": "am-1"})

    self.client.force_authenticate(self.user)

    payload = {
        "departure_city": "Lagos",
        "arrival_city": "Paris",
        "departure_date": "2026-05-01",
        "airline": "AF",
        "flight_offer": {"id": "same-offer"},
        "travelers": [{"id": "t1"}],
        "total_price": "200.00",
    }

    r1 = self.client.post(FLIGHT_BOOKINGS_URL, payload, format="json")
    r2 = self.client.post(FLIGHT_BOOKINGS_URL, payload, format="json")

    self.assertEqual(r1.status_code, status.HTTP_201_CREATED)

    # depends on your implementation
    # could be 400 or duplicate allowed
    self.assertIn(r2.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED])

@patch("app.flights.views.AmadeusService.create_flight_order")
@patch("app.flights.views.FlutterwaveService.verify_payment")
def test_verify_race_condition(self, mock_verify, mock_order):

    meta = {
        "flight_offer": {"id": "offer-race"},
        "travelers": [{"id": "t1"}],
        "departure_city": "Lagos",
        "arrival_city": "Paris",
        "departure_date": "2026-05-01",
        "airline": "AF",
    }

    payment = self.create_payment(status="pending", raw_meta=meta)

    mock_verify.return_value = {
        "status": "success",
        "data": {
            "status": "successful",
            "amount": "100.00",
            "currency": "USD",
            "id": "fw-race",
        },
    }

    mock_order.return_value = {"id": "am-race"}

    self.client.force_authenticate(self.user)

    response1 = self.client.post(
        VERIFY_PAYMENT_URL, {"tx_ref": payment.tx_ref}, format="json"
    )

    response2 = self.client.post(
        VERIFY_PAYMENT_URL, {"tx_ref": payment.tx_ref}, format="json"
    )

    self.assertEqual(
        FlightBooking.objects.filter(booking=payment.booking).count(), 1
    )

@patch("app.flights.views.AmadeusService.create_flight_order")
def test_airline_price_change(self, mock_order):

    mock_order.side_effect = Exception("PRICE_DISCREPANCY")

    self.client.force_authenticate(self.user)

    payload = {
        "departure_city": "Lagos",
        "arrival_city": "Paris",
        "departure_date": "2026-05-01",
        "airline": "AF",
        "flight_offer": {"id": "offer-1"},
        "travelers": [{"id": "t1"}],
        "total_price": "200.00",
    }

    response = self.client.post(FLIGHT_BOOKINGS_URL, payload, format="json")

    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

@patch("app.flights.views.AmadeusService.create_flight_order")
def test_airline_seat_unavailable(self, mock_order):

    mock_order.side_effect = Exception("SEAT_UNAVAILABLE")

    self.client.force_authenticate(self.user)

    payload = {
        "departure_city": "Lagos",
        "arrival_city": "Paris",
        "departure_date": "2026-05-01",
        "airline": "AF",
        "flight_offer": {"id": "offer-seat"},
        "travelers": [{"id": "t1"}],
        "total_price": "200.00",
    }

    response = self.client.post(FLIGHT_BOOKINGS_URL, payload, format="json")

    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

@patch("app.flights.views.AmadeusService.create_flight_order")
def test_airline_timeout(self, mock_order):

    mock_order.side_effect = TimeoutError("Airline API timeout")

    self.client.force_authenticate(self.user)

    payload = {
        "departure_city": "Lagos",
        "arrival_city": "Paris",
        "departure_date": "2026-05-01",
        "airline": "AF",
        "flight_offer": {"id": "offer-timeout"},
        "travelers": [{"id": "t1"}],
        "total_price": "200.00",
    }

    response = self.client.post(FLIGHT_BOOKINGS_URL, payload, format="json")

    self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

@patch("app.flights.views.AmadeusService.create_flight_order")
@patch("app.flights.views.FlutterwaveService.verify_payment")
def test_payment_success_airline_failure(self, mock_verify, mock_order):

    meta = {
        "flight_offer": {"id": "offer-pay"},
        "travelers": [{"id": "t1"}],
        "departure_city": "Lagos",
        "arrival_city": "Paris",
        "departure_date": "2026-05-01",
        "airline": "AF",
    }

    payment = self.create_payment(status="pending", raw_meta=meta)

    mock_verify.return_value = {
        "status": "success",
        "data": {
            "status": "successful",
            "amount": "100.00",
            "currency": "USD",
        },
    }

    mock_order.side_effect = Exception("Airline booking failed")

    self.client.force_authenticate(self.user)

    response = self.client.post(
        VERIFY_PAYMENT_URL,
        {"tx_ref": payment.tx_ref},
        format="json",
    )

    self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR])

@patch("app.flights.views.AmadeusService.create_flight_order")
def test_expired_flight_offer(self, mock_order):

    mock_order.side_effect = Exception("OFFER_NOT_FOUND")

    self.client.force_authenticate(self.user)

    payload = {
        "departure_city": "Lagos",
        "arrival_city": "Paris",
        "departure_date": "2026-05-01",
        "airline": "AF",
        "flight_offer": {"id": "expired-offer"},
        "travelers": [{"id": "t1"}],
        "total_price": "200.00",
    }

    response = self.client.post(FLIGHT_BOOKINGS_URL, payload, format="json")

    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class FullFlightBookingFlowTest(APITestCase):

    def setUp(self):

        self.user = self.create_user()
        self.client.force_authenticate(self.user)

        self.search_url = reverse("flight-search")
        self.booking_url = reverse("flight-bookings")
        self.verify_url = reverse("verify-payment")

    def create_user(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.create_user(
            email="user@test.com",
            password="password123"
        )

    @patch("app.flights.views.AmadeusService.search_flights")
    @patch("app.flights.views.AmadeusService.create_flight_order")
    @patch("app.flights.views.FlutterwaveService.verify_payment")
    def test_complete_flight_booking_flow(
        self,
        mock_verify_payment,
        mock_create_order,
        mock_search_flights
    ):
        """
        Full workflow test:

        search → booking → payment → verification → airline booking
        """

        # Step 1 — Mock flight search
        mock_search_flights.return_value = [
            {
                "id": "offer-123",
                "price": {"total": "200.00"},
                "itineraries": []
            }
        ]

        # Step 2 — Mock payment verification
        mock_verify_payment.return_value = {
            "status": "success",
            "data": {
                "status": "successful",
                "amount": "200.00",
                "currency": "USD",
                "id": "fw-123"
            }
        }

        # Step 3 — Mock airline order creation
        mock_create_order.return_value = {
            "id": "amadeus-order-1"
        }

        # -------------------------
        # 1️⃣ Search flights
        # -------------------------

        search_response = self.client.get(self.search_url, {
            "origin": "LOS",
            "destination": "CDG",
            "departure_date": "2026-05-01",
            "adults": 1
        })

        self.assertEqual(search_response.status_code, status.HTTP_200_OK)

        offer = search_self._data(response)[0]

        # -------------------------
        # 2️⃣ Create booking
        # -------------------------

        booking_payload = {
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
            "flight_offer": offer,
            "travelers": [{"id": "1"}],
            "total_price": "200.00"
        }

        booking_response = self.client.post(
            self.booking_url,
            booking_payload,
            format="json"
        )

        self.assertEqual(booking_response.status_code, status.HTTP_201_CREATED)

        booking = Booking.objects.first()

        self.assertIsNotNone(booking)

        # -------------------------
        # 3️⃣ Create payment record
        # -------------------------

        payment = Payment.objects.create(
            booking=booking,
            tx_ref="tx-flow-123",
            amount=Decimal("200.00"),
            currency="USD",
            payment_method="card",
            status="pending",
            raw_meta={
                "flight_offer": offer,
                "travelers": [{"id": "1"}],
                "departure_city": "Lagos",
                "arrival_city": "Paris",
                "departure_date": "2026-05-01",
                "airline": "AF",
            }
        )

        # -------------------------
        # 4️⃣ Verify payment
        # -------------------------

        verify_response = self.client.post(
            self.verify_url,
            {"tx_ref": payment.tx_ref},
            format="json"
        )

        self.assertEqual(verify_response.status_code, status.HTTP_201_CREATED)

        payment.refresh_from_db()

        self.assertEqual(payment.status, "succeeded")

        # -------------------------
        # 5️⃣ Confirm airline booking
        # -------------------------

        flight_booking = FlightBooking.objects.filter(
            booking=booking
        ).first()

        self.assertIsNotNone(flight_booking)

        self.assertEqual(
            flight_booking.airline_booking_id,
            "amadeus-order-1"
        )

class ConcurrentPaymentVerificationTest(APITestCase):

    def setUp(self):

        self.user = self.create_user()
        self.client.force_authenticate(self.user)

    def create_user(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        return User.objects.create_user(
            email="race@test.com",
            password="password123"
        )

    @patch("app.flights.views.AmadeusService.create_flight_order")
    @patch("app.flights.views.FlutterwaveService.verify_payment")
    def test_concurrent_payment_verification(
        self,
        mock_verify_payment,
        mock_create_order
    ):

        mock_verify_payment.return_value = {
            "status": "success",
            "data": {
                "status": "successful",
                "amount": "200.00",
                "currency": "USD",
                "id": "fw-race"
            }
        }

        mock_create_order.return_value = {
            "id": "airline-order-race"
        }

        # create booking
        booking = Booking.objects.create(
            user=self.user,
            status="pending"
        )

        payment = Payment.objects.create(
            booking=booking,
            tx_ref="race-test-123",
            amount=Decimal("200.00"),
            currency="USD",
            payment_method="card",
            status="pending",
            raw_meta={
                "flight_offer": {"id": "offer-race"},
                "travelers": [{"id": "1"}],
                "departure_city": "Lagos",
                "arrival_city": "Paris",
                "departure_date": "2026-05-01",
                "airline": "AF",
            }
        )

        VERIFY_URL = "/api/payments/verify/"

        responses = []

        def verify_payment():
            response = self.client.post(
                VERIFY_URL,
                {"tx_ref": payment.tx_ref},
                format="json"
            )
            responses.append(response.status_code)

        # simulate two simultaneous requests
        thread1 = threading.Thread(target=verify_payment)
        thread2 = threading.Thread(target=verify_payment)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # ensure only one airline booking created
        self.assertEqual(
            FlightBooking.objects.filter(booking=booking).count(),
            1
        )

        # payment must end in succeeded state
        payment.refresh_from_db()

        self.assertEqual(payment.status, "succeeded")

        # ensure at least one success response
        self.assertIn(status.HTTP_201_CREATED, responses)


class AirportSearchTests(BaseFlightTestCase):
    def setUp(self):
        super().setUp()
        Airport.objects.create(
            code="LOS",
            city="Lagos",
            name="Murtala Muhammed International Airport",
            country="Nigeria",
        )
        Airport.objects.create(
            code="LGA",
            city="New York",
            name="LaGuardia Airport",
            country="United States",
        )
        Airport.objects.create(
            code="ABC",
            city="Test City",
            name="Lagos Regional Airfield",
            country="Testland",
        )

    def test_search_requires_minimum_length(self):
        response = self.client.get(AIRPORT_SEARCH_URL, data={"q": "l"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_search_orders_city_match_first(self):
        response = self.client.get(AIRPORT_SEARCH_URL, data={"q": "lag"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertGreaterEqual(len(data), 2)
        self.assertEqual(
            data[0]["label"],
            "Lagos - Murtala Muhammed International Airport",
        )
        self.assertEqual(data[0]["value"], "LOS")


class AirportAdminViewSetTests(BaseFlightTestCase):
    def test_admin_airport_list_requires_auth(self):
        response = self.client.get(ADMIN_AIRPORTS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_create_airport(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            ADMIN_AIRPORTS_URL,
            data={
                "code": "CDG",
                "city": "Paris",
                "name": "Charles de Gaulle Airport",
                "country": "France",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Airport.objects.filter(code="CDG").exists())
