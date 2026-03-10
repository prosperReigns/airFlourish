from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from app.bookings.models import Booking
from app.payments.models import Payment
from app.payments.serializers import PaymentSerializer
from app.services.booking_engine import BookingEngine


class PaymentFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="payer@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)

        self.booking = BookingEngine.create_booking(
            user=self.user,
            service_type="hotel",
            total_price=Decimal("200.00"),
            currency="NGN",
        )

    @patch("app.payments.views.FlutterwaveService")
    def test_card_payment_initiation_creates_payment(self, mock_service):
        mock_service.return_value.initiate_card_payment.return_value = {
            "status": "success",
            "message": "Payment initiated",
        }

        payload = {
            "booking_id": self.booking.id,
            "amount": "200.00",
            "currency": "NGN",
            "tx_ref": "tx-ref-123",
        }
        headers = {
            "HTTP_IDEMPOTENCY_KEY": "idem-key-123",
            "HTTP_X_TRACE_ID": "trace-123",
        }

        response = self.client.post(
            "/api/payments/card/initiate/",
            payload,
            format="json",
            **headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Payment.objects.count(), 1)
        payment = Payment.objects.get(booking=self.booking)
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.payment_method, "card")
        self.assertEqual(payment.idempotency_key, "idem-key-123")

    @patch("app.payments.views.process_flight_booking")
    @patch("app.payments.views.FlutterwaveService")
    def test_payment_verification_marks_payment_and_booking(
        self, mock_service, mock_task
    ):
        mock_task.delay.return_value = None
        mock_service.return_value.verify_payment.return_value = {
            "status": "success",
            "data": {
                "status": "successful",
                "amount": "200.00",
                "currency": "NGN",
                "id": "fw-123",
            },
        }

        payment = Payment.objects.create(
            booking=self.booking,
            amount=Decimal("200.00"),
            currency="NGN",
            payment_method="card",
            tx_ref="tx-ref-verify",
            status="pending",
        )

        response = self.client.post(
            "/api/payments/verify/",
            {"tx_ref": payment.tx_ref},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(payment.status, "succeeded")
        self.assertEqual(self.booking.status, "confirmed")
        mock_task.delay.assert_called_once_with(self.booking.id)
        mock_service.return_value.verify_payment.assert_called_once_with(
            payment.tx_ref
        )

class PaymentModelTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="payer@example.com",
            password="password123",
            country="NG",
        )
        self.booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            total_price=Decimal("150.00"),
            currency="NGN",
            status="pending",
        )
    def test_payment_creation(self):
        payment = Payment.objects.create(
            booking=self.booking,
            amount=Decimal("150.00"),
            currency="NGN",
            payment_method="card",
            tx_ref="tx-ref-model-test",
            status="pending",
        )
        self.assertEqual(payment.booking, self.booking)
        self.assertEqual(payment.amount, Decimal("150.00"))
        self.assertEqual(payment.currency, "NGN")
        self.assertEqual(payment.payment_method, "card")
        self.assertEqual(payment.tx_ref, "tx-ref-model-test")
        self.assertEqual(payment.status, "pending")


class PaymentSerializerTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="serializerpayer@example.com",
            password="password123",
            country="NG",
        )
        self.booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            reference_code="PAY-TEST-001",
            total_price=Decimal("180.00"),
            currency="NGN",
            status="pending",
        )
        self.payment = Payment.objects.create(
            booking=self.booking,
            amount=Decimal("180.00"),
            currency="NGN",
            payment_method="card",
            tx_ref="tx-ref-serializer",
            status="pending",
        )

    def test_payment_serializer_outputs_expected_fields(self):
        data = PaymentSerializer(self.payment).data
        self.assertEqual(data["booking"], self.booking.id)
        self.assertEqual(data["amount"], "180.00")
        self.assertEqual(data["currency"], "NGN")
        self.assertEqual(data["payment_method"], "card")
        self.assertEqual(data["tx_ref"], "tx-ref-serializer")


class PaymentSerializerValidationTests(TestCase):
    def test_payment_serializer_missing_required_fields(self):
        serializer = PaymentSerializer(
            data={
                "amount": "120.00",
                "currency": "NGN",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("booking", serializer.errors)
        self.assertIn("payment_method", serializer.errors)
        self.assertIn("tx_ref", serializer.errors)

    def test_payment_serializer_invalid_amount(self):
        serializer = PaymentSerializer(
            data={
                "booking": "invalid-booking",
                "amount": "not-a-number",
                "currency": "NGN",
                "payment_method": "card",
                "tx_ref": "tx-invalid",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)

class PaymentAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="payer@example.com",
            password="password123",
            country="NG",
        )
        self.booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            total_price=Decimal("150.00"),
            currency="NGN",
            status="pending",
        )
    @patch("app.payments.views.FlutterwaveService")
    def test_card_payment_initiation(self, mock_service):
        mock_service.return_value.initiate_card_payment.return_value = {
            "status": "success",
            "message": "Payment initiated",
        }

        payload = {
            "booking_id": self.booking.id,
            "amount": "150.00",
            "currency": "NGN",
            "tx_ref": "tx-ref-api-test",
        }
        headers = {
            "HTTP_IDEMPOTENCY_KEY": "idem-key-api-test",
            "HTTP_X_TRACE_ID": "trace-api-test",
        }

        response = self.client.post(
            "/api/payments/card/initiate/",
            payload,
            format="json",
            **headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Payment.objects.count(), 1)
        payment = Payment.objects.get(booking=self.booking)
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.payment_method, "card")
        self.assertEqual(payment.idempotency_key, "idem-key-api-test")
    @patch("app.payments.views.process_flight_booking")
    @patch("app.payments.views.FlutterwaveService")
    def test_payment_verification(self, mock_service, mock_task):
        mock_task.delay.return_value = None
        mock_service.return_value.verify_payment.return_value = {
            "status": "success",
            "data": {
                "status": "successful",
                "amount": "150.00",
                "currency": "NGN",
                "id": "fw-verify-api-test",
            },
        }

        payment = Payment.objects.create(
            booking=self.booking,
            amount=Decimal("150.00"),
            currency="NGN",
            payment_method="card",
            tx_ref="tx-ref-verify-api-test",
            status="pending",
        )

        response = self.client.post(
            "/api/payments/verify/",
            {"tx_ref": payment.tx_ref},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(payment.status, "succeeded")
        self.assertEqual(self.booking.status, "confirmed")
        mock_task.delay.assert_called_once_with(self.booking.id)
        mock_service.return_value.verify_payment.assert_called_once_with(
            payment.tx_ref
        )

class PaymentEdgeCaseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="payer@example.com",
            password="password123",
            country="NG",
        )
        self.booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            total_price=Decimal("150.00"),
            currency="NGN",
            status="pending",
        )
    @patch("app.payments.views.FlutterwaveService")
    def test_payment_verification_with_failed_status(self, mock_service):
        mock_service.return_value.verify_payment.return_value = {
            "status": "success",
            "data": {
                "status": "failed",
                "amount": "150.00",
                "currency": "NGN",
                "id": "fw-failed-api-test",
            },
        }

        payment = Payment.objects.create(
            booking=self.booking,
            amount=Decimal("150.00"),
            currency="NGN",
            payment_method="card",
            tx_ref="tx-ref-failed-api-test",
            status="pending",
        )

        response = self.client.post(
            "/api/payments/verify/",
            {"tx_ref": payment.tx_ref},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(payment.status, "failed")
        self.assertEqual(self.booking.status, "pending")
        mock_service.return_value.verify_payment.assert_called_once_with(
            payment.tx_ref
        )

class AdminHotelTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="admin@example.com",
            password="password123",
            country="NG",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    @patch("app.hotels.views.FlutterwaveService")
    def test_admin_can_create_hotel(self, mock_service):
        mock_service.return_value.create_hotel.return_value = {
            "status": "success",
            "data": {
                "id": "hotel-api-test",
                "name": "Test Hotel",
                "location": "Test Location"
            }
        }

        response = self.client.post(
            "/api/hotels/",
            {
                "name": "Test Hotel",
                "location": "Test Location"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 201)
        mock_service.return_value.create_hotel.assert_called_once_with(
            name="Test Hotel",
            location="Test Location"
        )
    @patch("app.hotels.views.FlutterwaveService")
    def test_admin_can_create_hotel_with_create_hotel_endpoint(self, mock_service):
        mock_service.return_value.create_hotel.return_value = {
            "status": "success",
            "data": {
                "id": "hotel-create-hotel-api-test",
                "name": "Admin Test Hotel",
                "location": "Admin Test Location"
            }
        }
    
        response = self.client.post(
            "/api/hotels/create_hotel/",
            {
                "hotel_name": "Admin Test Hotel",
                "city": "Admin Test Location",
                "address": "123 Admin St",
                "country": "NG",
                "price_per_night": 10000.00,
                "currency": "NGN",
                "available_rooms": 10,
                "description": "A hotel created by an admin user for testing purposes.",
                "facilities": ["Free WiFi", "Pool", "Gym"],
                "images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
            },
            format="json"
        )

        self.assertEqual(response.status_code, 201)
        mock_service.return_value.create_hotel.assert_called_once_with(
            name="Admin Test Hotel",
            location="Admin Test Location"
        )

class UserAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
            country="NG"
        )
    def test_user_can_login_and_receive_tokens(self):
        response = self.client.post(
            "/api/token/",
            {"email": "user@example.com", "password": "password123"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["email"], "user@example.com")
    def test_user_can_logout_and_blacklist_token(self):
        # First, log in to get a refresh token
        login_response = self.client.post(
            "/api/token/",
            {"email": "user@example.com", "password": "password123"}
        )
        self.assertEqual(login_response.status_code, 200)
        refresh_token = login_response.data["refresh"]

        # Now, use the refresh token to logout
        logout_response = self.client.post(
            "/api/token/logout/",
            {"refresh": refresh_token}
        )
        self.assertEqual(logout_response.status_code, 200)
        # Attempt to use the refresh token again to get a new access token
        token_response = self.client.post(
            "/api/token/refresh/",
            {"refresh": refresh_token}
        )
        self.assertEqual(token_response.status_code, 401)  # Should be unauthorized since the token is blacklisted

class UserProfileTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
            country="NG"
        )
        self.client.force_authenticate(self.user)
    def test_user_can_retrieve_profile(self):
        response = self.client.get("/users/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "user@example.com")
        self.assertEqual(response.data["country"]["code"], "NG")
        self.assertEqual(response.data["country"]["name"], "Nigeria")

class UserRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
    def test_user_can_register(self):
        response = self.client.post(
            "/users/register/",
            {
                "email": "user@example.com",
                "password": "password123",
                "country": "NG"
            }
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["email"], "user@example.com")
        self.assertEqual(response.data["country"]["code"], "NG")
        self.assertEqual(response.data["country"]["name"], "Nigeria")
