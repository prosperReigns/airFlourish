from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from app.bookings.models import Booking
from app.hotels.models import Hotel, HotelReservation


class HotelFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
            country="NG",
        )
        self.client.force_authenticate(self.user)

        self.hotel = Hotel.objects.create(
            hotel_name="Test Hotel",
            city="Lagos",
            address="123 Main St",
            country="NG",
            price_per_night=Decimal("100.00"),
            currency="NGN",
            available_rooms=5,
        )

    def test_user_can_list_hotels(self):
        response = self.client.get("/api/hotels/hotels/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["hotel_name"], "Test Hotel")

    def test_user_can_book_hotel(self):
        payload = {
            "hotel_id": self.hotel.id,
            "check_in": "2026-04-10",
            "check_out": "2026-04-12",
            "guests": 2,
        }

        response = self.client.post(
            "/api/hotels/hotel-reservations/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(HotelReservation.objects.count(), 1)
        self.assertEqual(Booking.objects.count(), 1)

        reservation = HotelReservation.objects.first()
        self.assertEqual(reservation.hotel_name, self.hotel.hotel_name)
        self.assertEqual(reservation.booking.user, self.user)
        self.assertEqual(reservation.total_price, Decimal("200.00"))
