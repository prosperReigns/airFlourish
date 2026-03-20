from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from app.payments.models import Payment
from app.rentals.models import CarRental
from app.transport.models import Vehicle


_FW_PATCH = patch(
    "app.rentals.views.FlutterwaveService.initiate_card_payment",
    return_value={
        "status": "success",
        "data": {"link": "https://example.com/pay"},
    },
)


def setUpModule():
    _FW_PATCH.start()


def tearDownModule():
    _FW_PATCH.stop()


class CarRentalFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="rentaluser@example.com",
            password="password123",
            country="NG",
        )
        self.vehicle = Vehicle.objects.create(
            vehicle_type="sedan",
            plate_number="ABC-123",
            capacity=4,
            provider="Acme Rentals",
            status="available",
            is_active=True,
        )

    def test_user_can_create_rental(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/rentals/rentals/",
            {
                "vehicle": self.vehicle.id,
                "start_date": "2030-01-01T10:00:00Z",
                "end_date": "2030-01-03T10:00:00Z",
                "daily_rate": "100.00",
                "pickup_location": "Lagos",
                "dropoff_location": "Ikeja",
                "deposit_amount": "50.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(CarRental.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

    def test_user_can_cancel_rental(self):
        self.client.force_authenticate(self.user)
        create_response = self.client.post(
            "/api/rentals/rentals/",
            {
                "vehicle": self.vehicle.id,
                "start_date": "2030-02-01T10:00:00Z",
                "end_date": "2030-02-03T10:00:00Z",
                "daily_rate": "120.00",
            },
            format="json",
        )
        rental_id = create_response.data["rental_id"]
        cancel_response = self.client.post(
            f"/api/rentals/rentals/{rental_id}/cancel_reservation/",
            format="json",
        )
        self.assertEqual(cancel_response.status_code, 200)
        rental = CarRental.objects.get(id=rental_id)
        self.assertEqual(rental.status, "cancelled")
