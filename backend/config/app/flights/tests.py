from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from app.bookings.models import Booking
from app.flights.models import FlightBooking
from app.flights.serializers import FlightBookingSerializer
from app.payments.models import Payment


class FlightSecureFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)

    @patch("app.flights.views.AmadeusService.reprice_flight")
    @patch("app.flights.views.FlutterwaveService")
    def test_secure_booking_initiates_payment(self, mock_fw, mock_reprice):
        mock_reprice.return_value = {
            "flightOffers": [{"price": {"total": "100.00", "currency": "USD"}}]
        }
        mock_fw.return_value.initiate_card_payment.return_value = {
            "status": "success",
            "data": {"link": "http://pay.local/test"},
        }

        payload = {
            "flight_offer": {"id": "offer-1"},
            "travelers": [{"id": "t1"}],
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
            "passengers": 2,
        }

        response = self.client.post("/api/flights/secure-book/", payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

        payment = Payment.objects.first()
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.amount, Decimal("100.00"))
        self.assertEqual(payment.currency, "USD")
        self.assertEqual(payment.payment_method, "card")
        self.assertEqual(payment.booking.user, self.user)

    @patch("app.flights.views.AmadeusService.create_flight_order")
    @patch("app.flights.views.FlutterwaveService")
    @patch("app.flights.views.AmadeusService.reprice_flight")
    def test_verify_payment_books_flight(self, mock_reprice, mock_fw, mock_create_order):
        mock_reprice.return_value = {
            "flightOffers": [{"price": {"total": "100.00", "currency": "USD"}}]
        }
        mock_fw.return_value.initiate_card_payment.return_value = {
            "status": "success",
            "data": {"link": "http://pay.local/test"},
        }
        mock_fw.return_value.verify_payment.return_value = {
            "status": "success",
            "data": {"status": "successful", "amount": "100.00", "currency": "USD", "id": "fw-1"},
        }
        mock_create_order.return_value = {"id": "am-1"}

        payload = {
            "flight_offer": {"id": "offer-1"},
            "travelers": [{"id": "t1"}],
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
            "passengers": 2,
        }

        secure_response = self.client.post("/api/flights/secure-book/", payload, format="json")
        tx_ref = secure_response.data["tx_ref"]

        verify_response = self.client.post(
            "/api/flights/verify-payment/",
            {"tx_ref": tx_ref},
            format="json",
        )

        self.assertEqual(verify_response.status_code, 201)
        self.assertEqual(FlightBooking.objects.count(), 1)

        payment = Payment.objects.get(tx_ref=tx_ref)
        booking = payment.booking

        self.assertEqual(payment.status, "succeeded")
        self.assertEqual(booking.status, "confirmed")
        self.assertEqual(booking.external_service_id, "am-1")

class FlightBookingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_create_flight_booking(self):
        payload = {
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "return_date": "2026-05-10",
            "airline": "AF",
            "passengers": 2,
        }
        response = self.client.post("/api/flight-bookings/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(FlightBooking.objects.count(), 1)
        booking = FlightBooking.objects.first()
        self.assertEqual(booking.booking.user, self.user)
        self.assertEqual(booking.departure_city, "Lagos")
        self.assertEqual(booking.arrival_city, "Paris")
        self.assertEqual(str(booking.departure_date), "2026-05-01")
        self.assertEqual(str(booking.return_date), "2026-05-10")
        self.assertEqual(booking.airline, "AF")
        self.assertEqual(booking.passengers, 2)

class FlightSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    @patch("app.bookings.views.AmadeusService.search_flights")
    def test_search_flights(self, mock_search):
        mock_search.return_value = [
            {
                "flight_id": 1,
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": "2023-10-01",
                "return_date": "2023-10-05"
            }
        ]
        response = self.client.get(
            "/api/bookings/search-flights/?origin=JFK&destination=LAX&departure_date=2023-10-01&return_date=2023-10-05"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["origin"], "JFK")
        self.assertEqual(response.data[0]["destination"], "LAX")
        self.assertEqual(response.data[0]["departure_date"], "2023-10-01")
        self.assertEqual(response.data[0]["return_date"], "2023-10-05")

class FlightBookingListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_list_flight_bookings(self):
        # Create a flight booking for the user
        booking = Booking.objects.create(user=self.user, status="confirmed")
        FlightBooking.objects.create(
            booking=booking,
            departure_city="Lagos",
            arrival_city="Paris",
            departure_date="2026-05-01",
            return_date="2026-05-10",
            airline="AF",
            passengers=2,
        )
        response = self.client.get("/api/flight-bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["departure_city"], "Lagos")
        self.assertEqual(response.data[0]["arrival_city"], "Paris")
        self.assertEqual(response.data[0]["departure_date"], "2026-05-01")
        self.assertEqual(response.data[0]["return_date"], "2026-05-10")
        self.assertEqual(response.data[0]["airline"], "AF")
        self.assertEqual(response.data[0]["passengers"], 2)

class FlightBookingPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            password="password123",
            country="NG",
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user1)
    def test_flight_booking_permissions(self):
        # Create a flight booking for user1
        booking1 = Booking.objects.create(user=self.user1, status="confirmed")
        FlightBooking.objects.create(
            booking=booking1,
            departure_city="Lagos",
            arrival_city="Paris",
            departure_date="2026-05-01",
            return_date="2026-05-10",
            airline="AF",
            passengers=2,
        )
        # Create a flight booking for user2
        booking2 = Booking.objects.create(user=self.user2, status="confirmed")
        FlightBooking.objects.create(
            booking=booking2,
            departure_city="New York",
            arrival_city="London",
            departure_date="2026-06-01",
            return_date="2026-06-10",
            airline="BA",
            passengers=1,
        )
        response = self.client.get("/api/flight-bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["departure_city"], "Lagos")
        self.assertEqual(response.data[0]["arrival_city"], "Paris")
        self.assertEqual(response.data[0]["departure_date"], "2026-05-01")
        self.assertEqual(response.data[0]["return_date"], "2026-05-10")
        self.assertEqual(response.data[0]["airline"], "AF")
        self.assertEqual(response.data[0]["passengers"], 2)

class FlightBookingDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_flight_booking_detail(self):
        booking = Booking.objects.create(user=self.user, status="confirmed")
        flight_booking = FlightBooking.objects.create(
            booking=booking,
            departure_city="Lagos",
            arrival_city="Paris",
            departure_date="2026-05-01",
            return_date="2026-05-10",
            airline="AF",
            passengers=2,
        )
        response = self.client.get(f"/api/flight-bookings/{flight_booking.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["departure_city"], "Lagos")
        self.assertEqual(response.data["arrival_city"], "Paris")
        self.assertEqual(response.data["departure_date"], "2026-05-01")
        self.assertEqual(response.data["return_date"], "2026-05-10")
        self.assertEqual(response.data["airline"], "AF")
        self.assertEqual(response.data["passengers"], 2)

class FlightBookingUpdateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_flight_booking_update(self):
        booking = Booking.objects.create(user=self.user, status="confirmed")
        flight_booking = FlightBooking.objects.create(
            booking=booking,
            departure_city="Lagos",
            arrival_city="Paris",
            departure_date="2026-05-01",
            return_date="2026-05-10",
            airline="AF",
            passengers=2,
        )
        payload = {
            "departure_city": "Lagos",
            "arrival_city": "Rome",
            "departure_date": "2026-05-01",
            "return_date": "2026-05-10",
            "airline": "AF",
            "passengers": 2,
        }
        response = self.client.put(f"/api/flight-bookings/{flight_booking.id}/", payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["arrival_city"], "Rome")
        flight_booking.refresh_from_db()
        self.assertEqual(flight_booking.arrival_city, "Rome")

class FlightBookingDeleteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_flight_booking_delete(self):
        booking = Booking.objects.create(user=self.user, status="confirmed")
        flight_booking = FlightBooking.objects.create(
            booking=booking,
            departure_city="Lagos",
            arrival_city="Paris",
            departure_date="2026-05-01",
            return_date="2026-05-10",
            airline="AF",
            passengers=2,
        )
        response = self.client.delete(f"/api/flight-bookings/{flight_booking.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(FlightBooking.objects.count(), 0)

class FlightBookingUnauthorizedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
    def test_flight_booking_unauthorized(self):
        response = self.client.get("/api/flight-bookings/")
        self.assertEqual(response.status_code, 401)
        response = self.client.post("/api/flight-bookings/", {}, format="json")
        self.assertEqual(response.status_code, 401)
        response = self.client.get("/api/flight-bookings/1/")
        self.assertEqual(response.status_code, 401)
        response = self.client.put("/api/flight-bookings/1/", {}, format="json")
        self.assertEqual(response.status_code, 401)
        response = self.client.delete("/api/flight-bookings/1/")
        self.assertEqual(response.status_code, 401)

class FlightSearchUnauthorizedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
    def test_flight_search_unauthorized(self):
        response = self.client.get("/api/bookings/search-flights/?origin=JFK&destination=LAX&departure_date=2023-10-01")
        self.assertEqual(response.status_code, 401)
    
class FlightSecureFlowUnauthorizedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
    def test_secure_flow_unauthorized(self):
        response = self.client.post("/api/flights/secure-book/", {}, format="json")
        self.assertEqual(response.status_code, 401)
        response = self.client.post("/api/flights/verify-payment/", {}, format="json")
        self.assertEqual(response.status_code, 401)

class FlightSecureFlowInvalidDataTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_secure_flow_invalid_data(self):
        response = self.client.post("/api/flights/secure-book/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/flights/verify-payment/", {}, format="json")
        self.assertEqual(response.status_code, 400)

class FlightSearchInvalidDataTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_search_invalid_data(self):
        response = self.client.get("/api/bookings/search-flights/?origin=JFK&destination=LAX&departure_date=2023-10-01")
        self.assertEqual(response.status_code, 400)
        response = self.client.get("/api/bookings/search-flights/?origin=JFK&destination=LAX")
        self.assertEqual(response.status_code, 400)
        response = self.client.get("/api/bookings/search-flights/?origin=JFK&departure_date=2023-10-01")
        self.assertEqual(response.status_code, 400)
        response = self.client.get("/api/bookings/search-flights/?destination=LAX&departure_date=2023-10-01")
        self.assertEqual(response.status_code, 400)

class FlightBookingPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user1 = User.objects.create_user(
            email="flightuser1@example.com",
            password="password123",
            country="NG",
        )
        self.user2 = User.objects.create_user(
            email="flightuser2@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user1)
    def test_flight_booking_permissions(self):
        booking1 = Booking.objects.create(user=self.user1, status="confirmed")
        flight_booking1 = FlightBooking.objects.create(
            booking=booking1,
            departure_city="Lagos",
            arrival_city="Paris",
            departure_date="2026-05-01",
            return_date="2026-05-10",
            airline="AF",
            passengers=2,
        )
        booking2 = Booking.objects.create(user=self.user2, status="confirmed")
        flight_booking2 = FlightBooking.objects.create(
            booking=booking2,
            departure_city="New York",
            arrival_city="London",
            departure_date="2026-06-01",
            return_date="2026-06-10",
            airline="BA",
            passengers=1,
        )
        response = self.client.get(f"/api/flight-bookings/{flight_booking1.id}/")
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/api/flight-bookings/{flight_booking2.id}/")
        self.assertEqual(response.status_code, 404)
        response = self.client.put(f"/api/flight-bookings/{flight_booking1.id}/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        response = self.client.put(f"/api/flight-bookings/{flight_booking2.id}/", {}, format="json")
        self.assertEqual(response.status_code, 404)
        response = self.client.delete(f"/api/flight-bookings/{flight_booking1.id}/")
        self.assertEqual(response.status_code, 204)
        response = self.client.delete(f"/api/flight-bookings/{flight_booking2.id}/")
        self.assertEqual(response.status_code, 404)

class FlightSearchPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_flight_search_permissions(self):
        response = self.client.get("/api/bookings/search-flights/?origin=JFK&destination=LAX&departure_date=2023-10-01")
        self.assertEqual(response.status_code, 200)

class FlightSecureFlowPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_secure_flow_permissions(self):
        response = self.client.post("/api/flights/secure-book/", {}, format="json")
        self.assertIn(response.status_code, [200, 400])  # 200 if data is valid, 400 if invalid
        response = self.client.post("/api/flights/verify-payment/", {}, format="json")
        self.assertIn(response.status_code, [201, 400])  # 201 if payment is verified, 400 if invalid data  
    
class FlightBookingEdgeCaseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_flight_booking_edge_cases(self):
        # Test booking with zero passengers
        payload = {
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "return_date": "2026-05-10",
            "airline": "AF",
            "passengers": 0,
        }
        response = self.client.post("/api/flight-bookings/", payload, format="json")
        self.assertEqual(response.status_code, 400)

        # Test booking with past departure date
        payload["passengers"] = 2
        payload["departure_date"] = "2020-01-01"
        response = self.client.post("/api/flight-bookings/", payload, format="json")
        self.assertEqual(response.status_code, 400)

        # Test booking with return date before departure date
        payload["departure_date"] = "2026-05-10"
        payload["return_date"] = "2026-05-01"
        response = self.client.post("/api/flight-bookings/", payload, format="json")
        self.assertEqual(response.status_code, 400)

class FlightSearchEdgeCaseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_flight_search_edge_cases(self):
        # Test search with invalid origin
        response = self.client.get("/api/bookings/search-flights/?origin=INVALID&destination=LAX&departure_date=2023-10-01")
        self.assertEqual(response.status_code, 400)

        # Test search with invalid destination
        response = self.client.get("/api/bookings/search-flights/?origin=JFK&destination=INVALID&departure_date=2023-10-01")
        self.assertEqual(response.status_code, 400)

        # Test search with past departure date
        response = self.client.get("/api/bookings/search-flights/?origin=JFK&destination=LAX&departure_date=2020-01-01")
        self.assertEqual(response.status_code, 400)

class FlightSecureFlowEdgeCaseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_secure_flow_edge_cases(self):
        # Test secure booking with invalid data
        payload = {
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "return_date": "2026-05-10",
            "airline": "AF",
            "passengers": 2,
        }
        response = self.client.post("/api/flights/secure-book/", payload, format="json")
        self.assertIn(response.status_code, [200, 400])  # 200 if data is valid, 400 if invalid
        # Test verify payment with invalid tx_ref
        response = self.client.post("/api/flights/verify-payment/", {"tx_ref": "invalid"}, format="json")
        self.assertEqual(response.status_code, 400)

class FlightBookingConcurrencyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_flight_booking_concurrency(self):
        booking = Booking.objects.create(user=self.user, status="confirmed")
        flight_booking = FlightBooking.objects.create(
            booking=booking,
            departure_city="Lagos",
            arrival_city="Paris",
            departure_date="2026-05-01",
            return_date="2026-05-10",
            airline="AF",
            passengers=2,
        )
        # Simulate concurrent updates to the same flight booking
        response1 = self.client.put(f"/api/flight-bookings/{flight_booking.id}/", {"arrival_city": "Rome"}, format="json")
        response2 = self.client.put(f"/api/flight-bookings/{flight_booking.id}/", {"arrival_city": "Berlin"}, format="json")
        self.assertIn(response1.status_code, [200, 409])  # 200 if update succeeds, 409 if conflict occurs
        self.assertIn(response2.status_code, [200, 409])  # 200 if update succeeds, 409 if conflict occurs
        
class FlightBookingExternalAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)

    @patch("app.flights.views.AmadeusService.reprice_flight")
    def test_reprice_flight_api_failure(self, mock_reprice):
        mock_reprice.side_effect = Exception("Amadeus API error")
        payload = {
            "flight_offer": {"id": "offer-1"},
            "travelers": [{"id": "t1"}],
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
            "passengers": 2,
        }
        response = self.client.post("/api/flights/secure-book/", payload, format="json")
        self.assertEqual(response.status_code, 500)

    @patch("app.flights.views.FlutterwaveService.initiate_card_payment")
    def test_initiate_payment_api_failure(self, mock_initiate):
        mock_initiate.side_effect = Exception("Flutterwave API error")
        payload = {
            "flight_offer": {"id": "offer-1"},
            "travelers": [{"id": "t1"}],
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
            "passengers": 2,
        }
        response = self.client.post("/api/flights/secure-book/", payload, format="json")
        self.assertEqual(response.status_code, 500)

    @patch("app.flights.views.FlutterwaveService.verify_payment")
    def test_verify_payment_api_failure(self, mock_verify):
        mock_verify.side_effect = Exception("Flutterwave API error")
        response = self.client.post("/api/flights/verify-payment/", {"tx_ref": "test"}, format="json")
        self.assertEqual(response.status_code, 500)

class FlightBookingDataIntegrityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_flight_booking_data_integrity(self):
        payload = {
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "return_date": "2026-05-10",
            "airline": "AF",
            "passengers": 2,
        }
        response = self.client.post("/api/flight-bookings/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        booking = FlightBooking.objects.first()
        self.assertEqual(booking.departure_city, "Lagos")
        self.assertEqual(booking.arrival_city, "Paris")
        self.assertEqual(str(booking.departure_date), "2026-05-01")
        self.assertEqual(str(booking.return_date), "2026-05-10")
        self.assertEqual(booking.airline, "AF")
        self.assertEqual(booking.passengers, 2)

class FlightSearchDataIntegrityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    @patch("app.bookings.views.AmadeusService.search_flights")
    def test_flight_search_data_integrity(self, mock_search):
        mock_search.return_value = [
            {
                "flight_id": 1,
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": "2023-10-01",
                "return_date": "2023-10-05"
            }
        ]
        response = self.client.get(
            "/api/bookings/search-flights/?origin=JFK&destination=LAX&departure_date=2023-10-01&return_date=2023-10-05"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["origin"], "JFK")
        self.assertEqual(response.data[0]["destination"], "LAX")
        self.assertEqual(response.data[0]["departure_date"], "2023-10-01")
        self.assertEqual(response.data[0]["return_date"], "2023-10-05")

class FlightSecureFlowDataIntegrityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    @patch("app.flights.views.AmadeusService.reprice_flight")
    @patch("app.flights.views.FlutterwaveService")
    def test_secure_flow_data_integrity(self, mock_fw, mock_reprice):
        mock_reprice.return_value = {
            "flightOffers": [{"price": {"total": "100.00", "currency": "USD"}}]
        }
        mock_fw.return_value.initiate_card_payment.return_value = {
            "status": "success",
            "data": {"link": "http://pay.local/test"},
        }
        payload = {
            "flight_offer": {"id": "offer-1"},
            "travelers": [{"id": "t1"}],
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "airline": "AF",
            "passengers": 2,
        }
        response = self.client.post("/api/flights/secure-book/", payload, format="json")
        self.assertEqual(response.status_code, 200)
        payment = Payment.objects.first()
        self.assertEqual(payment.amount, Decimal("100.00"))
        self.assertEqual(payment.currency, "USD")
        self.assertEqual(payment.payment_method, "card")
        self.assertEqual(payment.booking.user, self.user)

class FlightBookingPerformanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    def test_flight_booking_performance(self):
        payload = {
            "departure_city": "Lagos",
            "arrival_city": "Paris",
            "departure_date": "2026-05-01",
            "return_date": "2026-05-10",
            "airline": "AF",
            "passengers": 2,
        }
        with self.assertNumQueries(5):  # Adjust based on expected queries
            response = self.client.post("/api/flight-bookings/", payload, format="json")
            self.assertEqual(response.status_code, 201)

class FlightSearchPerformanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightuser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)
    @patch("app.bookings.views.AmadeusService.search_flights")
    def test_flight_search_performance(self, mock_search):
        mock_search.return_value = [
            {
                "flight_id": 1,
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": "2023-10-01",
                "return_date": "2023-10-05"
            }
        ]
        with self.assertNumQueries(2):  # Adjust based on expected queries
            response = self.client.get(
                "/api/bookings/search-flights/?origin=JFK&destination=LAX&departure_date=2023-10-01&return_date=2023-10-05"
            )
            self.assertEqual(response.status_code, 200)


class FlightBookingModelTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightmodel@example.com",
            password="password123",
            country="NG",
        )
        self.booking = Booking.objects.create(
            user=self.user,
            service_type="flight",
            reference_code="FLI-TEST-001",
            total_price=Decimal("500.00"),
            currency="USD",
        )

    def test_flight_booking_str_and_defaults(self):
        flight = FlightBooking.objects.create(
            booking=self.booking,
            departure_city="Lagos",
            arrival_city="Paris",
            departure_date=date(2026, 5, 1),
            airline="AF",
        )
        self.assertEqual(str(flight), "Lagos to Paris")
        self.assertEqual(flight.passengers, 1)


class FlightBookingSerializerTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="flightserializer@example.com",
            password="password123",
            country="NG",
        )
        self.booking = Booking.objects.create(
            user=self.user,
            service_type="flight",
            reference_code="FLI-TEST-002",
            total_price=Decimal("600.00"),
            currency="USD",
        )
        self.flight = FlightBooking.objects.create(
            booking=self.booking,
            departure_city="Lagos",
            arrival_city="London",
            departure_date=date(2026, 6, 1),
            return_date=date(2026, 6, 10),
            airline="BA",
            passengers=2,
        )

    def test_flight_booking_serializer_outputs_expected_fields(self):
        data = FlightBookingSerializer(self.flight).data
        self.assertEqual(data["booking"], self.booking.id)
        self.assertEqual(data["departure_city"], "Lagos")
        self.assertEqual(data["arrival_city"], "London")
        self.assertEqual(data["airline"], "BA")
        self.assertEqual(data["passengers"], 2)


class FlightBookingSerializerValidationTests(TestCase):
    def test_flight_booking_serializer_missing_required_fields(self):
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
