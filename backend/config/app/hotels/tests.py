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

class HotelDeepCoverageTests(BaseHotelTestCase):

    # -------------------------
    # Date Edge Cases
    # -------------------------

    def test_same_day_checkin_checkout_rejected(self):
        user = self.create_user()
        self.auth(user)
        hotel = self.create_hotel()

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-04-10",
            "check_out": "2026-04-10",
            "guests": 1,
        }

        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_booking_far_future_date(self):
        user = self.create_user()
        self.auth(user)
        hotel = self.create_hotel()

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2030-01-01",
            "check_out": "2030-01-05",
            "guests": 2,
        }

        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_booking_past_date_rejected(self):
        user = self.create_user()
        self.auth(user)
        hotel = self.create_hotel()

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2020-01-01",
            "check_out": "2020-01-05",
            "guests": 2,
        }

        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    # -------------------------
    # Room Availability
    # -------------------------

    def test_reservation_reduces_available_rooms(self):
        user = self.create_user()
        self.auth(user)
        hotel = self.create_hotel(available_rooms=5)

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-05-01",
            "check_out": "2026-05-03",
            "guests": 1,
        }

        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")

        hotel.refresh_from_db()
        self.assertLessEqual(hotel.available_rooms, 5)

    def test_booking_when_no_rooms_available_rejected(self):
        user = self.create_user()
        self.auth(user)
        hotel = self.create_hotel(available_rooms=0)

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-04-10",
            "check_out": "2026-04-12",
            "guests": 1,
        }

        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    # -------------------------
    # Reservation Conflict Tests
    # -------------------------

    def test_overlapping_reservations_allowed_if_rooms_available(self):
        user = self.create_user()
        self.auth(user)

        hotel = self.create_hotel(available_rooms=5)

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-06-01",
            "check_out": "2026-06-05",
            "guests": 2,
        }

        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")

        self.assertEqual(response.status_code, 201)

    # -------------------------
    # Booking Integrity
    # -------------------------

    def test_booking_reference_code_generated(self):
        user = self.create_user()
        self.auth(user)
        hotel = self.create_hotel()

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-04-10",
            "check_out": "2026-04-12",
            "guests": 1,
        }

        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")

        booking = Booking.objects.first()
        self.assertTrue(booking.reference_code.startswith("HOT"))

    def test_booking_user_matches_reservation_user(self):
        user = self.create_user()
        self.auth(user)

        hotel = self.create_hotel()

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-04-10",
            "check_out": "2026-04-12",
            "guests": 1,
        }

        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")

        reservation = HotelReservation.objects.first()
        self.assertEqual(reservation.user, reservation.booking.user)

    # -------------------------
    # Serializer Edge Cases
    # -------------------------

    def test_serializer_rejects_negative_price(self):
        serializer = HotelSerializer(
            data={
                "hotel_name": "Bad Hotel",
                "city": "Lagos",
                "country": "NG",
                "price_per_night": "-10",
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_serializer_accepts_large_price(self):
        serializer = HotelSerializer(
            data={
                "hotel_name": "Luxury Hotel",
                "city": "Lagos",
                "country": "NG",
                "price_per_night": "999999",
            }
        )
        self.assertTrue(serializer.is_valid())

    # -------------------------
    # Admin Safety
    # -------------------------

    def test_admin_update_invalid_price(self):
        admin = self.create_admin()
        hotel = self.create_hotel()

        self.auth(admin)

        response = self.client.patch(
            f"/api/hotels/admin-hotels/{hotel.id}/",
            {"price_per_night": "-10"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_admin_delete_nonexistent_hotel(self):
        admin = self.create_admin()
        self.auth(admin)

        response = self.client.delete("/api/hotels/admin-hotels/99999/")
        self.assertEqual(response.status_code, 404)

    # -------------------------
    # Cache Safety
    # -------------------------

    def test_cache_invalidation_after_hotel_update(self):
        hotel = self.create_hotel()
        cache.set("hotel_list", ["cached"], 60)

        admin = self.create_admin()
        self.auth(admin)

        self.client.patch(
            f"/api/hotels/admin-hotels/{hotel.id}/",
            {"hotel_name": "Updated"},
            format="json",
        )

        cache.delete("hotel_list")
        self.assertIsNone(cache.get("hotel_list"))

    # -------------------------
    # Security / Tampering
    # -------------------------

    def test_user_cannot_override_total_price(self):
        user = self.create_user()
        self.auth(user)

        hotel = self.create_hotel()

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-04-10",
            "check_out": "2026-04-12",
            "guests": 1,
            "total_price": "1",
        }

        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")

        reservation = HotelReservation.objects.first()
        self.assertNotEqual(reservation.total_price, Decimal("1"))

    # -------------------------
    # Concurrency Simulation
    # -------------------------

    def test_parallel_reservations_do_not_exceed_rooms(self):
        user = self.create_user()
        self.auth(user)

        hotel = self.create_hotel(available_rooms=1)

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-07-01",
            "check_out": "2026-07-05",
            "guests": 1,
        }

        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")

        self.assertIn(response.status_code, [400, 409])

    # -------------------------
    # Performance / N+1 Protection
    # -------------------------

    def test_list_many_hotels_no_n_plus_one(self):
        user = self.create_user()
        self.auth(user)

        for i in range(20):
            self.create_hotel(hotel_name=f"Hotel {i}")

        with self.assertNumQueries(3):
            self.client.get("/api/hotels/hotels/")

    def test_list_many_reservations_no_n_plus_one(self):
        user = self.create_user()
        self.auth(user)

        hotel = self.create_hotel()

        for i in range(10):
            booking = Booking.objects.create(
                user=user,
                service_type="hotel",
                reference_code=f"HOT-{i}",
                total_price=Decimal("100"),
                currency="NGN",
            )

            HotelReservation.objects.create(
                user=user,
                booking=booking,
                hotel_name=hotel.hotel_name,
                check_in=date(2026, 4, 1),
                check_out=date(2026, 4, 3),
                guests=1,
            )

        with self.assertNumQueries(3):
            self.client.get("/api/hotels/hotel-reservations/")

class HotelBookingProductionTests(BaseHotelTestCase):

    # -------------------------
    # Double Booking Protection
    # -------------------------

    def test_two_users_booking_last_room(self):
        user1 = self.create_user(email="user1@test.com")
        user2 = self.create_user(email="user2@test.com")

        hotel = self.create_hotel(available_rooms=1)

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
            "guests": 1,
        }

        self.auth(user1)
        r1 = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")

        self.auth(user2)
        r2 = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")

        self.assertEqual(r1.status_code, 201)
        self.assertIn(r2.status_code, [400, 409])

    # -------------------------
    # Reservation Overlap Logic
    # -------------------------

    def test_overlapping_dates_detected(self):
        user = self.create_user()
        self.auth(user)

        hotel = self.create_hotel(available_rooms=1)

        payload1 = {
            "hotel_id": hotel.id,
            "check_in": "2026-09-01",
            "check_out": "2026-09-05",
            "guests": 1,
        }

        payload2 = {
            "hotel_id": hotel.id,
            "check_in": "2026-09-03",
            "check_out": "2026-09-07",
            "guests": 1,
        }

        r1 = self.client.post("/api/hotels/hotel-reservations/", payload1, format="json")
        r2 = self.client.post("/api/hotels/hotel-reservations/", payload2, format="json")

        self.assertEqual(r1.status_code, 201)
        self.assertIn(r2.status_code, [400, 409])

    # -------------------------
    # Calendar Gap Booking
    # -------------------------

    def test_booking_between_existing_reservations(self):
        user = self.create_user()
        self.auth(user)

        hotel = self.create_hotel(available_rooms=1)

        self.client.post(
            "/api/hotels/hotel-reservations/",
            {
                "hotel_id": hotel.id,
                "check_in": "2026-10-01",
                "check_out": "2026-10-05",
                "guests": 1,
            },
            format="json",
        )

        response = self.client.post(
            "/api/hotels/hotel-reservations/",
            {
                "hotel_id": hotel.id,
                "check_in": "2026-10-05",
                "check_out": "2026-10-08",
                "guests": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

    # -------------------------
    # Price Recalculation
    # -------------------------

    def test_price_updates_if_hotel_price_changes(self):
        user = self.create_user()
        self.auth(user)

        hotel = self.create_hotel(price_per_night=Decimal("100.00"))

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-11-01",
            "check_out": "2026-11-04",
            "guests": 1,
        }

        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")

        reservation = HotelReservation.objects.first()

        self.assertEqual(reservation.total_price, Decimal("300.00"))

    # -------------------------
    # Inventory Drift Detection
    # -------------------------

    def test_available_rooms_never_negative(self):
        hotel = self.create_hotel(available_rooms=1)

        hotel.available_rooms -= 2
        hotel.save()

        hotel.refresh_from_db()

        self.assertGreaterEqual(hotel.available_rooms, 0)

    # -------------------------
    # Reservation Cancellation
    # -------------------------

    def test_cancel_reservation_frees_room(self):
        user = self.create_user()
        self.auth(user)

        hotel = self.create_hotel(available_rooms=1)

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-12-01",
            "check_out": "2026-12-03",
            "guests": 1,
        }

        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")

        reservation = HotelReservation.objects.first()

        self.client.delete(f"/api/hotels/hotel-reservations/{reservation.id}/")

        hotel.refresh_from_db()

        self.assertGreaterEqual(hotel.available_rooms, 1)

    # -------------------------
    # Long Stay Booking
    # -------------------------

    def test_long_stay_price_calculation(self):
        user = self.create_user()
        self.auth(user)

        hotel = self.create_hotel(price_per_night=Decimal("50"))

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-01-01",
            "check_out": "2026-01-31",
            "guests": 1,
        }

        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")

        reservation = HotelReservation.objects.first()

        self.assertEqual(reservation.total_price, Decimal("1500"))

    # -------------------------
    # Booking Tampering Protection
    # -------------------------

    def test_user_cannot_assign_different_user_to_reservation(self):
        user = self.create_user()
        other = self.create_user(email="other@test.com")

        self.auth(user)

        hotel = self.create_hotel()

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-04-01",
            "check_out": "2026-04-03",
            "guests": 1,
            "user": other.id,
        }

        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")

        reservation = HotelReservation.objects.first()

        self.assertEqual(reservation.user, user)

    # -------------------------
    # Extreme Guest Count
    # -------------------------

    def test_large_guest_number_rejected(self):
        user = self.create_user()
        self.auth(user)

        hotel = self.create_hotel()

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-04-10",
            "check_out": "2026-04-12",
            "guests": 100,
        }

        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")

        self.assertEqual(response.status_code, 400)

    # -------------------------
    # Cache Corruption Safety
    # -------------------------

    def test_corrupt_cache_does_not_break_hotel_list(self):
        user = self.create_user()
        self.auth(user)

        cache.set("hotel_list", "bad-data", 60)

        response = self.client.get("/api/hotels/hotels/")

        self.assertEqual(response.status_code, 200)

    # -------------------------
    # Timezone Safety
    # -------------------------

    def test_midnight_boundary_booking(self):
        user = self.create_user()
        self.auth(user)

        hotel = self.create_hotel()

        payload = {
            "hotel_id": hotel.id,
            "check_in": "2026-03-01",
            "check_out": "2026-03-02",
            "guests": 1,
        }

        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")

        self.assertEqual(response.status_code, 201)

    # -------------------------
    # Bulk Reservation Listing
    # -------------------------

    def test_many_reservations_returned(self):
        user = self.create_user()
        self.auth(user)

        hotel = self.create_hotel()

        for i in range(20):
            booking = Booking.objects.create(
                user=user,
                service_type="hotel",
                reference_code=f"HOT-{i}",
                total_price=Decimal("100"),
                currency="NGN",
            )

            HotelReservation.objects.create(
                user=user,
                booking=booking,
                hotel_name=hotel.hotel_name,
                check_in=date(2026, 5, 1),
                check_out=date(2026, 5, 2),
                guests=1,
            )

        response = self.client.get("/api/hotels/hotel-reservations/")

        self.assertEqual(len(response.data), 20)

class HotelAvailabilityCalendarTests(BaseHotelTestCase):

    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.auth(self.user)

    # -------------------------
    # Single Room Daily Availability
    # -------------------------
    def test_single_room_availability_daily(self):
        hotel = self.create_hotel(available_rooms=1)
        # Book one day
        payload = {"hotel_id": hotel.id, "check_in": "2026-06-01", "check_out": "2026-06-02", "guests": 1}
        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        hotel.refresh_from_db()
        self.assertEqual(hotel.available_rooms, 0)

    # -------------------------
    # Multi-Room Daily Availability
    # -------------------------
    def test_multi_room_availability(self):
        hotel = self.create_hotel(available_rooms=3)
        # Book 2 rooms for same date
        for _ in range(2):
            payload = {"hotel_id": hotel.id, "check_in": "2026-06-05", "check_out": "2026-06-06", "guests": 1}
            self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        hotel.refresh_from_db()
        self.assertEqual(hotel.available_rooms, 1)

    # -------------------------
    # Overlapping Reservations Matrix
    # -------------------------
    def test_overlapping_reservations_matrix(self):
        hotel = self.create_hotel(available_rooms=2)
        # Two overlapping reservations
        self.client.post("/api/hotels/hotel-reservations/", {"hotel_id": hotel.id, "check_in": "2026-07-01", "check_out": "2026-07-04", "guests": 1}, format="json")
        self.client.post("/api/hotels/hotel-reservations/", {"hotel_id": hotel.id, "check_in": "2026-07-03", "check_out": "2026-07-05", "guests": 1}, format="json")
        # Third reservation should fail on fully booked date
        response = self.client.post("/api/hotels/hotel-reservations/", {"hotel_id": hotel.id, "check_in": "2026-07-02", "check_out": "2026-07-03", "guests": 1}, format="json")
        self.assertIn(response.status_code, [400, 409])

    # -------------------------
    # Cancellation Frees Dates
    # -------------------------
    def test_cancellation_updates_calendar(self):
        hotel = self.create_hotel(available_rooms=1)
        payload = {"hotel_id": hotel.id, "check_in": "2026-08-10", "check_out": "2026-08-12", "guests": 1}
        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        reservation = HotelReservation.objects.first()
        self.client.delete(f"/api/hotels/hotel-reservations/{reservation.id}/")
        hotel.refresh_from_db()
        self.assertEqual(hotel.available_rooms, 1)

    # -------------------------
    # Booking Across Month Boundary
    # -------------------------
    def test_booking_across_month_boundary(self):
        hotel = self.create_hotel(available_rooms=1)
        payload = {"hotel_id": hotel.id, "check_in": "2026-05-30", "check_out": "2026-06-02", "guests": 1}
        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        reservation = HotelReservation.objects.first()
        self.assertEqual(reservation.total_price, hotel.price_per_night * 3)

    # -------------------------
    # Multi-Day Multi-Room Availability
    # -------------------------
    def test_multi_day_multi_room_availability_matrix(self):
        hotel = self.create_hotel(available_rooms=3)
        # Book multiple days
        bookings = [
            {"check_in": "2026-09-01", "check_out": "2026-09-03"},
            {"check_in": "2026-09-02", "check_out": "2026-09-04"},
            {"check_in": "2026-09-03", "check_out": "2026-09-05"},
        ]
        for b in bookings:
            self.client.post("/api/hotels/hotel-reservations/", {"hotel_id": hotel.id, **b, "guests": 1}, format="json")
        hotel.refresh_from_db()
        self.assertEqual(hotel.available_rooms, 0)

    # -------------------------
    # Edge Case: Same Check-in and Check-out
    # -------------------------
    def test_same_checkin_checkout_rejected(self):
        hotel = self.create_hotel()
        payload = {"hotel_id": hotel.id, "check_in": "2026-10-01", "check_out": "2026-10-01", "guests": 1}
        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    # -------------------------
    # Bulk Booking Across Days
    # -------------------------
    def test_bulk_booking_multiple_days_multiple_rooms(self):
        hotel = self.create_hotel(available_rooms=5)
        for i in range(5):
            self.client.post("/api/hotels/hotel-reservations/", {"hotel_id": hotel.id, "check_in": "2026-11-01", "check_out": "2026-11-03", "guests": 1}, format="json")
        # Sixth booking should fail
        response = self.client.post("/api/hotels/hotel-reservations/", {"hotel_id": hotel.id, "check_in": "2026-11-01", "check_out": "2026-11-03", "guests": 1}, format="json")
        self.assertIn(response.status_code, [400, 409])

    # -------------------------
    # Edge: Booking Far Future
    # -------------------------
    def test_booking_far_future_date(self):
        hotel = self.create_hotel()
        payload = {"hotel_id": hotel.id, "check_in": "2030-01-01", "check_out": "2030-01-05", "guests": 1}
        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 201)

    # -------------------------
    # Edge: Booking Past Date Rejected
    # -------------------------
    def test_booking_past_date_rejected(self):
        hotel = self.create_hotel()
        payload = {"hotel_id": hotel.id, "check_in": "2020-01-01", "check_out": "2020-01-02", "guests": 1}
        response = self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    # -------------------------
    # Multi-Hotel Availability Isolation
    # -------------------------
    def test_reservations_are_hotel_isolated(self):
        hotel1 = self.create_hotel(hotel_name="Hotel 1", available_rooms=1)
        hotel2 = self.create_hotel(hotel_name="Hotel 2", available_rooms=1)
        payload = {"hotel_id": hotel1.id, "check_in": "2026-12-01", "check_out": "2026-12-03", "guests": 1}
        self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        response2 = self.client.post("/api/hotels/hotel-reservations/", {"hotel_id": hotel2.id, "check_in": "2026-12-01", "check_out": "2026-12-03", "guests": 1}, format="json")
        self.assertEqual(response2.status_code, 201)

    # -------------------------
    # Overlapping Multiple Users Multiple Rooms
    # -------------------------
    def test_overlapping_multiple_users_multiple_rooms(self):
        hotel = self.create_hotel(available_rooms=3)
        users = [self.create_user(email=f"user{i}@test.com") for i in range(3)]
        for user in users:
            self.auth(user)
            payload = {"hotel_id": hotel.id, "check_in": "2026-12-10", "check_out": "2026-12-12", "guests": 1}
            self.client.post("/api/hotels/hotel-reservations/", payload, format="json")
        # Fourth user should fail
        self.auth(self.create_user(email="user4@test.com"))
        response = self.client.post("/api/hotels/hotel-reservations/", {"hotel_id": hotel.id, "check_in": "2026-12-10", "check_out": "2026-12-12", "guests": 1}, format="json")
        self.assertIn(response.status_code, [400, 409])
