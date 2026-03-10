from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from app.bookings.models import Booking
from app.visas.models import VisaApplication


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
