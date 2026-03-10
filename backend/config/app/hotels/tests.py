from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from app.bookings.models import Booking
from app.hotels.models import Hotel, HotelReservation
from app.hotels.serializers import HotelReservationSerializer, HotelSerializer


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


class HotelModelTests(TestCase):
    def test_hotel_str(self):
        hotel = Hotel.objects.create(
            hotel_name="Model Hotel",
            city="Lagos",
            address="123 Model St",
            country="NG",
            price_per_night=Decimal("150.00"),
            currency="NGN",
            available_rooms=3,
        )
        self.assertEqual(str(hotel), "Model Hotel")


class HotelReservationModelTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="hotelmodel@example.com",
            password="password123",
            country="NG",
        )
        self.booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            reference_code="HOT-RES-001",
            total_price=Decimal("300.00"),
            currency="NGN",
        )

    def test_hotel_reservation_defaults(self):
        reservation = HotelReservation.objects.create(
            user=self.user,
            booking=self.booking,
            hotel_name="Model Hotel",
            check_in=date(2026, 4, 1),
            check_out=date(2026, 4, 5),
            guests=2,
        )
        self.assertEqual(reservation.status, "pending")
        self.assertIsNone(reservation.total_price)
        self.assertEqual(reservation.booking, self.booking)


class HotelSerializerTests(TestCase):
    def test_hotel_serializer_outputs_expected_fields(self):
        hotel = Hotel.objects.create(
            hotel_name="Serializer Hotel",
            city="Lagos",
            address="123 Serializer St",
            country="NG",
            price_per_night=Decimal("120.00"),
            currency="NGN",
            available_rooms=5,
        )
        data = HotelSerializer(hotel).data
        self.assertEqual(data["hotel_name"], "Serializer Hotel")
        self.assertEqual(data["city"], "Lagos")
        self.assertEqual(data["currency"], "NGN")
        self.assertIn(data["country"], [hotel.country.code, hotel.country.name])


class HotelReservationSerializerTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="hotelserializer@example.com",
            password="password123",
            country="NG",
        )
        self.booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            reference_code="HOT-RES-002",
            total_price=Decimal("400.00"),
            currency="NGN",
        )
        self.reservation = HotelReservation.objects.create(
            user=self.user,
            booking=self.booking,
            hotel_name="Serializer Hotel",
            check_in=date(2026, 4, 10),
            check_out=date(2026, 4, 12),
            guests=2,
            total_price=Decimal("240.00"),
        )

    def test_hotel_reservation_serializer_outputs_expected_fields(self):
        data = HotelReservationSerializer(self.reservation).data
        self.assertEqual(data["user"], self.user.id)
        self.assertEqual(data["booking"], self.booking.id)
        self.assertEqual(data["hotel_name"], "Serializer Hotel")
        self.assertEqual(data["guests"], 2)
        self.assertEqual(str(data["total_price"]), "240.00")


class HotelSerializerValidationTests(TestCase):
    def test_hotel_serializer_missing_required_fields(self):
        serializer = HotelSerializer(
            data={
                "city": "Lagos",
                "country": "NG",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("hotel_name", serializer.errors)

    def test_hotel_serializer_invalid_country(self):
        serializer = HotelSerializer(
            data={
                "hotel_name": "Invalid Country Hotel",
                "city": "Lagos",
                "country": "INVALID",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("country", serializer.errors)


class HotelReservationSerializerValidationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="hotelvalidation@example.com",
            password="password123",
            country="NG",
        )
        self.booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            reference_code="HOT-RES-003",
            total_price=Decimal("400.00"),
            currency="NGN",
        )

    def test_hotel_reservation_serializer_missing_required_fields(self):
        serializer = HotelReservationSerializer(
            data={
                "booking": self.booking.id,
                "check_in": "2026-04-10",
                "check_out": "2026-04-12",
                "guests": 2,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("hotel_name", serializer.errors)

    def test_hotel_reservation_serializer_invalid_date(self):
        serializer = HotelReservationSerializer(
            data={
                "booking": self.booking.id,
                "hotel_name": "Hotel",
                "check_in": "not-a-date",
                "check_out": "2026-04-12",
                "guests": 2,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("check_in", serializer.errors)
