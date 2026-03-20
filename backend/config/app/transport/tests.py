from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from app.payments.models import Payment
from app.transport.models import Trip, TransportBooking


_FW_PATCH = patch(
    "app.transport.views.FlutterwaveService.initiate_card_payment",
    return_value={
        "status": "success",
        "data": {"link": "https://example.com/pay"},
    },
)


def setUpModule():
    _FW_PATCH.start()


def tearDownModule():
    _FW_PATCH.stop()


class TransportBookingFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="transportuser@example.com",
            password="password123",
            country="NG",
        )
        self.admin = User.objects.create_user(
            email="transportadmin@example.com",
            password="password123",
            country="NG",
            user_type="admin",
        )
        self.trip = Trip.objects.create(
            name="Airport Shuttle",
            pickup_location="Lagos",
            dropoff_location="Ikeja",
            departure_time="2030-01-01T10:00:00Z",
            arrival_time="2030-01-01T11:00:00Z",
            capacity=3,
            booked_seats=1,
            price_per_seat=Decimal("50.00"),
            currency="NGN",
            status="scheduled",
        )

    def test_user_can_list_available_trips(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/transport/trips/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data.get("results", response.data)), 1)

    def test_user_can_create_transport_booking(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/transport/bookings/",
            {"trip": self.trip.id, "passengers": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.booked_seats, 2)
        self.assertEqual(TransportBooking.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

    def test_overbooking_is_prevented(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/transport/bookings/",
            {"trip": self.trip.id, "passengers": 5},
            format="json",
        )
        self.assertEqual(response.status_code, 409)

    def test_user_can_cancel_booking(self):
        self.client.force_authenticate(self.user)
        create_response = self.client.post(
            "/api/transport/bookings/",
            {"trip": self.trip.id, "passengers": 1},
            format="json",
        )
        booking_id = create_response.data["transport_booking_id"]
        cancel_response = self.client.post(
            f"/api/transport/bookings/{booking_id}/cancel_booking/",
            format="json",
        )
        self.assertEqual(cancel_response.status_code, 200)
        booking = TransportBooking.objects.get(id=booking_id)
        self.assertEqual(booking.status, "cancelled")
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.booked_seats, 1)

    def test_admin_can_start_and_complete_trip(self):
        self.client.force_authenticate(self.admin)
        start_response = self.client.post(
            f"/api/transport/admin/trips/{self.trip.id}/start_trip/",
            format="json",
        )
        self.assertEqual(start_response.status_code, 200)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, "en_route")

        complete_response = self.client.post(
            f"/api/transport/admin/trips/{self.trip.id}/complete_trip/",
            format="json",
        )
        self.assertEqual(complete_response.status_code, 200)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, "completed")
