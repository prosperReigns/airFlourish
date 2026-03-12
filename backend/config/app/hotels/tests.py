from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from app.bookings.models import Booking
from app.hotels.models import Hotel, HotelReservation
from app.hotels.serializers import HotelReservationSerializer, HotelSerializer


class BaseHotelTestCase(TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()
        self.User = get_user_model()

    def create_user(self, **overrides):
        defaults = {
            "email": "user@example.com",
            "password": "password123",
            "country": "NG",
        }
        defaults.update(overrides)
        return self.User.objects.create_user(**defaults)

    def create_admin(self, **overrides):
        defaults = {
            "email": "admin@example.com",
            "password": "password123",
            "country": "NG",
            "user_type": "admin",
        }
        defaults.update(overrides)
        return self.User.objects.create_user(**defaults)

    def create_hotel(self, **overrides):
        defaults = {
            "hotel_name": "Test Hotel",
            "city": "Lagos",
            "address": "123 Main St",
            "country": "NG",
            "price_per_night": Decimal("100.00"),
            "currency": "NGN",
            "available_rooms": 5,
        }
        defaults.update(overrides)
        return Hotel.objects.create(**defaults)

    def auth(self, user):
        self.client.force_authenticate(user)


class HotelFlowTests(BaseHotelTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.auth(self.user)
        self.hotel = self.create_hotel()

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


class HotelModelTests(BaseHotelTestCase):
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


class HotelReservationModelTests(BaseHotelTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(email="hotelmodel@example.com")
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


class HotelSerializerTests(BaseHotelTestCase):
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


class HotelReservationSerializerTests(BaseHotelTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(email="hotelserializer@example.com")
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


class HotelSerializerValidationTests(BaseHotelTestCase):
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


class HotelReservationSerializerValidationTests(BaseHotelTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(email="hotelvalidation@example.com")
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


class HotelAPISecurityTests(BaseHotelTestCase):
    def setUp(self):
        super().setUp()
        self.hotel = self.create_hotel()

    def test_list_requires_auth(self):
        response = self.client.get("/api/hotels/hotels/")
        self.assertEqual(response.status_code, 401)

    def test_retrieve_requires_auth(self):
        response = self.client.get(f"/api/hotels/hotels/{self.hotel.id}/")
        self.assertEqual(response.status_code, 401)

    def test_reservations_requires_auth(self):
        response = self.client.get("/api/hotels/hotel-reservations/")
        self.assertEqual(response.status_code, 401)


class HotelListAPITests(BaseHotelTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.auth(self.user)

    def test_list_returns_multiple_hotels(self):
        self.create_hotel(hotel_name="Hotel A")
        self.create_hotel(hotel_name="Hotel B")
        response = self.client.get("/api/hotels/hotels/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_list_returns_empty_when_none(self):
        response = self.client.get("/api/hotels/hotels/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_retrieve_returns_expected_fields(self):
        hotel = self.create_hotel(hotel_name="Field Hotel", city="Abuja")
        response = self.client.get(f"/api/hotels/hotels/{hotel.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["hotel_name"], "Field Hotel")
        self.assertEqual(response.data["city"], "Abuja")

    def test_retrieve_returns_404_for_missing(self):
        response = self.client.get("/api/hotels/hotels/99999/")
        self.assertEqual(response.status_code, 404)


class HotelReservationCreateValidationTests(BaseHotelTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.auth(self.user)
        self.hotel = self.create_hotel()

    def _payload(self):
        return {
            "hotel_id": self.hotel.id,
            "check_in": "2026-04-10",
            "check_out": "2026-04-12",
            "guests": 2,
        }

    def test_create_missing_hotel_id(self):
        payload = self._payload()
        payload.pop("hotel_id")
        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_missing_check_in(self):
        payload = self._payload()
        payload.pop("check_in")
        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_missing_check_out(self):
        payload = self._payload()
        payload.pop("check_out")
        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_invalid_guests(self):
        payload = self._payload()
        payload["guests"] = 0
        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_hotel_not_found(self):
        payload = self._payload()
        payload["hotel_id"] = 99999
        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 404)

    def test_create_invalid_date_format(self):
        payload = self._payload()
        payload["check_in"] = "not-a-date"
        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_check_out_before_check_in(self):
        payload = self._payload()
        payload["check_out"] = "2026-04-09"
        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_hotel_price_missing(self):
        self.hotel.price_per_night = None
        self.hotel.save()
        payload = self._payload()
        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)


class HotelReservationAccessTests(BaseHotelTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(email="user1@example.com")
        self.other_user = self.create_user(email="user2@example.com")
        self.admin = self.create_admin(email="admin-access@example.com")
        self.hotel = self.create_hotel()

        self.user_booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            reference_code="HOT-USER-001",
            total_price=Decimal("200.00"),
            currency="NGN",
        )
        self.other_booking = Booking.objects.create(
            user=self.other_user,
            service_type="hotel",
            reference_code="HOT-USER-002",
            total_price=Decimal("200.00"),
            currency="NGN",
        )
        self.user_reservation = HotelReservation.objects.create(
            user=self.user,
            booking=self.user_booking,
            hotel_name=self.hotel.hotel_name,
            check_in=date(2026, 4, 10),
            check_out=date(2026, 4, 12),
            guests=2,
            total_price=Decimal("200.00"),
        )
        self.other_reservation = HotelReservation.objects.create(
            user=self.other_user,
            booking=self.other_booking,
            hotel_name=self.hotel.hotel_name,
            check_in=date(2026, 4, 11),
            check_out=date(2026, 4, 13),
            guests=1,
            total_price=Decimal("200.00"),
        )

    def test_user_sees_only_own_reservations(self):
        self.auth(self.user)
        response = self.client.get("/api/hotels/hotel-reservations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.user_reservation.id)

    def test_admin_sees_all_reservations(self):
        self.auth(self.admin)
        response = self.client.get("/api/hotels/hotel-reservations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_user_cannot_retrieve_other_reservation(self):
        self.auth(self.user)
        response = self.client.get(f"/api/hotels/hotel-reservations/{self.other_reservation.id}/")
        self.assertEqual(response.status_code, 404)

    def test_user_can_update_own_reservation(self):
        self.auth(self.user)
        response = self.client.patch(
            f"/api/hotels/hotel-reservations/{self.user_reservation.id}/",
            {"guests": 3},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.user_reservation.refresh_from_db()
        self.assertEqual(self.user_reservation.guests, 3)

    def test_user_cannot_delete_other_reservation(self):
        self.auth(self.user)
        response = self.client.delete(f"/api/hotels/hotel-reservations/{self.other_reservation.id}/")
        self.assertEqual(response.status_code, 404)

    def test_user_can_delete_own_reservation(self):
        self.auth(self.user)
        response = self.client.delete(f"/api/hotels/hotel-reservations/{self.user_reservation.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(HotelReservation.objects.filter(id=self.user_reservation.id).exists())


class HotelReservationBehaviorTests(BaseHotelTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.auth(self.user)
        self.hotel = self.create_hotel(price_per_night=Decimal("150.00"))

    def test_booking_service_type_hotel(self):
        payload = {
            "hotel_id": self.hotel.id,
            "check_in": "2026-04-10",
            "check_out": "2026-04-12",
            "guests": 2,
        }
        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        booking = Booking.objects.first()
        self.assertEqual(booking.service_type, "hotel")

    def test_booking_currency_default_when_empty(self):
        self.hotel.currency = ""
        self.hotel.save()
        payload = {
            "hotel_id": self.hotel.id,
            "check_in": "2026-04-10",
            "check_out": "2026-04-12",
            "guests": 2,
        }
        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        booking = Booking.objects.first()
        self.assertEqual(booking.currency, "NGN")

    def test_total_price_calculates_nights(self):
        payload = {
            "hotel_id": self.hotel.id,
            "check_in": "2026-04-10",
            "check_out": "2026-04-13",
            "guests": 2,
        }
        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        reservation = HotelReservation.objects.first()
        self.assertEqual(reservation.total_price, Decimal("450.00"))

    def test_guests_string_cast(self):
        payload = {
            "hotel_id": self.hotel.id,
            "check_in": "2026-04-10",
            "check_out": "2026-04-12",
            "guests": "3",
        }
        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        reservation = HotelReservation.objects.first()
        self.assertEqual(reservation.guests, 3)


class AdminHotelAPITests(BaseHotelTestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.create_admin()
        self.user = self.create_user(email="regular@example.com")
        self.hotel = self.create_hotel()

    def test_non_admin_denied_admin_list(self):
        self.auth(self.user)
        response = self.client.get("/api/hotels/admin-hotels/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_hotels(self):
        self.auth(self.admin)
        response = self.client.get("/api/hotels/admin-hotels/")
        self.assertEqual(response.status_code, 200)

    def test_admin_can_create_hotel(self):
        self.auth(self.admin)
        payload = {
            "hotel_name": "Admin Hotel",
            "city": "Lagos",
            "address": "Admin Address",
            "country": "NG",
            "price_per_night": "200.00",
            "currency": "NGN",
            "available_rooms": 10,
        }
        response = self.client.post("/api/hotels/admin-hotels/", payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_admin_can_update_hotel(self):
        self.auth(self.admin)
        response = self.client.patch(
            f"/api/hotels/admin-hotels/{self.hotel.id}/",
            {"hotel_name": "Updated Hotel"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_can_delete_hotel(self):
        self.auth(self.admin)
        response = self.client.delete(f"/api/hotels/admin-hotels/{self.hotel.id}/")
        self.assertEqual(response.status_code, 204)

    def test_admin_legacy_create_hotel(self):
        self.auth(self.admin)
        payload = {
            "hotel_name": "Legacy Hotel",
            "city": "Lagos",
            "address": "Legacy Address",
            "country": "NG",
            "price_per_night": "180.00",
            "currency": "NGN",
            "available_rooms": 8,
        }
        response = self.client.post("/api/hotels/admin-hotels/create_hotel/", payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_admin_legacy_get_hotel(self):
        self.auth(self.admin)
        response = self.client.get(f"/api/hotels/admin-hotels/get_hotel/{self.hotel.id}/")
        self.assertEqual(response.status_code, 200)

    def test_admin_legacy_get_all_hotels(self):
        self.auth(self.admin)
        response = self.client.get("/api/hotels/admin-hotels/get_all_hotels/")
        self.assertEqual(response.status_code, 200)


class HotelSerializerExtraTests(BaseHotelTestCase):
    def test_hotel_defaults_currency(self):
        hotel = Hotel.objects.create(
            hotel_name="Default Currency Hotel",
            city="Lagos",
            address="Default St",
            country="NG",
            price_per_night=Decimal("100.00"),
        )
        self.assertEqual(hotel.currency, "NGN")

    def test_hotel_defaults_available_rooms(self):
        hotel = Hotel.objects.create(
            hotel_name="Default Rooms Hotel",
            city="Lagos",
            address="Default St",
            country="NG",
            price_per_night=Decimal("100.00"),
        )
        self.assertEqual(hotel.available_rooms, 1)

    def test_hotel_serializer_handles_images_facilities(self):
        hotel = Hotel.objects.create(
            hotel_name="Media Hotel",
            city="Lagos",
            address="Media St",
            country="NG",
            price_per_night=Decimal("100.00"),
            images=["img1", "img2"],
            facilities=["wifi", "pool"],
        )
        data = HotelSerializer(hotel).data
        self.assertEqual(data["images"], ["img1", "img2"])
        self.assertEqual(data["facilities"], ["wifi", "pool"])

    def test_hotel_serializer_handles_rooms(self):
        hotel = Hotel.objects.create(
            hotel_name="Rooms Hotel",
            city="Lagos",
            address="Rooms St",
            country="NG",
            price_per_night=Decimal("100.00"),
            rooms=[{"type": "standard", "count": 2}],
        )
        data = HotelSerializer(hotel).data
        self.assertEqual(data["rooms"], [{"type": "standard", "count": 2}])

    def test_reservation_str_contains_hotel_name(self):
        user = self.create_user()
        booking = Booking.objects.create(
            user=user,
            service_type="hotel",
            reference_code="HOT-STR-001",
            total_price=Decimal("200.00"),
            currency="NGN",
        )
        reservation = HotelReservation.objects.create(
            user=user,
            booking=booking,
            hotel_name="String Hotel",
            check_in=date(2026, 4, 10),
            check_out=date(2026, 4, 12),
            guests=1,
        )
        self.assertIn("String Hotel", str(reservation))


class HotelCachingTests(BaseHotelTestCase):
    def test_cache_roundtrip_hotel_list(self):
        hotel = self.create_hotel(hotel_name="Cache Hotel")
        data = HotelSerializer([hotel], many=True).data
        cache.set("hotels:list:cache", data, 60)
        cached = cache.get("hotels:list:cache")
        self.assertEqual(cached, data)

    def test_cache_separates_keys(self):
        cache.set("hotels:list:user:1", ["a"], 60)
        cache.set("hotels:list:user:2", ["b"], 60)
        self.assertEqual(cache.get("hotels:list:user:1"), ["a"])
        self.assertEqual(cache.get("hotels:list:user:2"), ["b"])


class HotelPerformanceTests(BaseHotelTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.auth(self.user)
        self.create_hotel(hotel_name="Perf Hotel")

    def test_list_hotels_query_count(self):
        with self.assertNumQueries(3):
            self.client.get("/api/hotels/hotels/")

    def test_list_reservations_query_count(self):
        booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            reference_code="HOT-PERF-001",
            total_price=Decimal("200.00"),
            currency="NGN",
        )
        HotelReservation.objects.create(
            user=self.user,
            booking=booking,
            hotel_name="Perf Hotel",
            check_in=date(2026, 4, 10),
            check_out=date(2026, 4, 12),
            guests=1,
        )
        with self.assertNumQueries(3):
            self.client.get("/api/hotels/hotel-reservations/")


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": ("app.users.authentication.CustomJWTAuthentication",),
        "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
        "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.UserRateThrottle",),
        "DEFAULT_THROTTLE_RATES": {"user": "1/minute"},
    }
)
class HotelRateLimitingTests(BaseHotelTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.auth(self.user)
        self.hotel = self.create_hotel()

    def test_rate_limit_hotel_list(self):
        first = self.client.get("/api/hotels/hotels/")
        second = self.client.get("/api/hotels/hotels/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)

    def test_rate_limit_hotel_reservation_create(self):
        payload = {
            "hotel_id": self.hotel.id,
            "check_in": "2026-04-10",
            "check_out": "2026-04-12",
            "guests": 1,
        }
        first = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        second = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 429)
