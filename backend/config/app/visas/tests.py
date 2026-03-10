from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from app.bookings.models import Booking
from app.visas.models import VisaApplication
from app.visas.serializers import VisaApplicationSerializer


class VisaFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="visauser@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)

    def test_can_create_visa_without_flight(self):
        payload = {
            "destination_country": "France",
            "visa_type": "tourist",
            "appointment_date": "2026-04-15",
            "visa_fee": "150.00",
            "currency": "NGN",
        }

        response = self.client.post("/api/visas/visas/", payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(VisaApplication.objects.count(), 1)

        visa = VisaApplication.objects.first()
        self.assertIsNone(visa.flight)

        booking = Booking.objects.get(id=visa.booking_id)
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.service_type, "visa")
        self.assertEqual(booking.total_price, Decimal("150.00"))


class VisaApplicationModelTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="visamodel@example.com",
            password="password123",
            country="NG",
        )
        self.booking = Booking.objects.create(
            user=self.user,
            service_type="visa",
            reference_code="VISA-TEST-001",
            total_price=Decimal("200.00"),
            currency="NGN",
        )

    def test_visa_application_defaults(self):
        visa = VisaApplication.objects.create(
            booking=self.booking,
            destination_country="France",
            visa_type="tourist",
            appointment_date=date(2026, 4, 15),
        )
        self.assertEqual(visa.status, "pending")
        self.assertEqual(visa.document_status, "pending")
        self.assertIsNone(visa.flight)


class VisaApplicationSerializerTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="visaserializer@example.com",
            password="password123",
            country="NG",
        )
        self.booking = Booking.objects.create(
            user=self.user,
            service_type="visa",
            reference_code="VISA-TEST-002",
            total_price=Decimal("250.00"),
            currency="NGN",
        )
        self.visa = VisaApplication.objects.create(
            booking=self.booking,
            destination_country="Italy",
            visa_type="business",
            appointment_date=date(2026, 5, 1),
            status="verified",
        )

    def test_visa_application_serializer_outputs_expected_fields(self):
        data = VisaApplicationSerializer(self.visa).data
        self.assertEqual(data["booking"], self.booking.id)
        self.assertEqual(data["destination_country"], "Italy")
        self.assertEqual(data["visa_type"], "business")
        self.assertEqual(data["status"], "verified")


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
