from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from app.hotels.models import Hotel
from app.users.views import User
from app.users.models import User
from rest_framework.test import APIClient

from app.bookings.models import Booking
from app.services.booking_engine import BookingEngine


class BookingViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user1@example.com",
            password="password123",
            country="NG",
        )
        self.other_user = User.objects.create_user(
            email="user2@example.com",
            password="password123",
            country="NG",
        )

        BookingEngine.create_booking(
            user=self.user,
            service_type="hotel",
            total_price=Decimal("150.00"),
            currency="NGN",
        )
        BookingEngine.create_booking(
            user=self.other_user,
            service_type="hotel",
            total_price=Decimal("250.00"),
            currency="NGN",
        )

    def test_regular_user_sees_only_own_bookings(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/bookings/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["user"],
            self.user.id,
        )

        self.assertEqual(Booking.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Booking.objects.filter(user=self.other_user).count(), 1)
    def test_admin_user_sees_all_bookings(self):
        admin_user = User.objects.create_user(
            email="admin@example.com",
            password="password123",
            country="NG",
            is_staff=True,
        )
        self.client.force_authenticate(admin_user)
        response = self.client.get("/api/bookings/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        user_ids = {booking["user"] for booking in response.data}
        self.assertIn(self.user.id, user_ids)
        self.assertIn(self.other_user.id, user_ids)
        self.assertEqual(Booking.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Booking.objects.filter(user=self.other_user).count(), 1)

class HotelViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_admin_can_create_hotel(self):
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.post("/api/hotels/", {"name": "Test Hotel", "location": "Test Location"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Hotel.objects.count(), 1)
        self.assertEqual(Hotel.objects.get().name, "Test Hotel")
        self.assertEqual(Hotel.objects.get().location, "Test Location")

    def test_non_admin_cannot_create_hotel(self):
        regular_user = User.objects.create_user(email="user@example.com", password="password123", country="NG")
        self.client.force_authenticate(regular_user)
        response = self.client.post("/api/hotels/", {"name": "Test Hotel", "location": "Test Location"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Hotel.objects.count(), 0)

    def test_admin_can_retrieve_hotel(self):
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.get(f"/api/hotels/{hotel.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Test Hotel")
        self.assertEqual(response.data["location"], "Test Location")

    def test_non_admin_can_retrieve_hotel(self):
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        regular_user = User.objects.create_user(email="user@example.com", password="password123", country="NG")
        self.client.force_authenticate(regular_user)
        response = self.client.get(f"/api/hotels/{hotel.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Test Hotel")
        self.assertEqual(response.data["location"], "Test Location")

    def test_admin_can_update_hotel(self):
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.put(f"/api/hotels/{hotel.id}/", {"name": "Updated Hotel", "location": "Updated Location"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Hotel.objects.get().name, "Updated Hotel")
        self.assertEqual(Hotel.objects.get().location, "Updated Location")

    def test_non_admin_cannot_update_hotel(self):
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        regular_user = User.objects.create_user(email="user@example.com", password="password123", country="NG")
        self.client.force_authenticate(regular_user)
        response = self.client.put(f"/api/hotels/{hotel.id}/", {"name": "Updated Hotel", "location": "Updated Location"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Hotel.objects.get().name, "Test Hotel")
        self.assertEqual(Hotel.objects.get().location, "Test Location")

class AdminHotelViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_admin_can_create_hotel_via_custom_endpoint(self):
            """Test that an admin user can create a hotel using the custom create_hotel endpoint."""
            admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
            self.client.force_authenticate(admin_user)
            response = self.client.post("/api/admin/hotels/", {"name": "Test Hotel", "location": "Test Location"})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(Hotel.objects.count(), 1)
            self.assertEqual(Hotel.objects.get().name, "Test Hotel")
            self.assertEqual(Hotel.objects.get().location, "Test Location")

    def test_admin_can_retrieve_hotel_via_custom_endpoint(self):
        """Test that an admin user can retrieve a hotel using the custom get_hotel endpoint."""
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.get(f"/api/admin/hotels/get_hotel/{hotel.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Test Hotel")
        self.assertEqual(response.data["location"], "Test Location")

    def test_admin_can_retrieve_all_hotels_via_custom_endpoint(self):
        """Test that an admin user can retrieve all hotels using the custom get_all_hotels endpoint."""
        Hotel.objects.create(name="Hotel 1", location="Location 1")
        Hotel.objects.create(name="Hotel 2", location="Location 2")
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.get("/api/admin/hotels/get_all_hotels/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        hotel_names = {hotel["name"] for hotel in response.data}
        self.assertIn("Hotel 1", hotel_names)
        self.assertIn("Hotel 2", hotel_names)

class BookingViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
            country="NG"
        )
        self.other_user = User.objects.create_user(
            email="otheruser@example.com",
            password="password123",
            country="NG"
        )
        BookingEngine.create_booking(
            user=self.user,
            service_type="hotel",
            total_price=Decimal("150.00"),
            currency="NGN",
        )
        BookingEngine.create_booking(
            user=self.other_user,
            service_type="hotel",
            total_price=Decimal("250.00"),
            currency="NGN",

        )
    def test_regular_user_sees_only_own_bookings(self):
        """Test that a regular user can only see their own bookings."""
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/bookings/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["user"],
            self.user.id,

            )
        self.assertEqual(Booking.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Booking.objects.filter(user=self.other_user).count(), 1)
    def test_admin_user_sees_all_bookings(self):
        """Test that an admin user can see all bookings."""
        admin_user = User.objects.create_user(
            email="admin@example.com",
            password="password123",
            country="NG",
            is_staff=True
        )
        self.client.force_authenticate(admin_user)
        response = self.client.get("/api/bookings/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        user_ids = {booking["user"] for booking in response.data}
        self.assertIn(self.user.id, user_ids)
        self.assertIn(self.other_user.id, user_ids)
        self.assertEqual(Booking.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Booking.objects.filter(user=self.other_user).count(), 1)

class HotelViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_admin_can_create_hotel(self):
        """Test that an admin user can create a hotel through the API."""
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.post("/api/admin/hotels/", data={"name": "Test Hotel", "location": "Test Location"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Hotel.objects.count(), 1)
        self.assertEqual(Hotel.objects.get().name, "Test Hotel")
        self.assertEqual(Hotel.objects.get().location, "Test Location")
    def test_non_admin_cannot_create_hotel(self):
        """Test that a non-admin user cannot create a hotel through the API."""
        regular_user = User.objects.create_user(email="regular@example.com", password="password123", country="NG")
        self.client.force_authenticate(regular_user)
        response = self.client.post("/api/admin/hotels/", data={"name": "Test Hotel", "location": "Test Location"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Hotel.objects.count(), 0)
    def test_admin_can_retrieve_hotel(self):
        """Test that an admin user can retrieve a hotel through the API."""
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.get(f"/api/admin/hotels/{hotel.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Test Hotel")
        self.assertEqual(response.data["location"], "Test Location")
    def test_non_admin_can_retrieve_hotel(self):
        """Test that a non-admin user can retrieve a hotel through the API."""
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        regular_user = User.objects.create_user(email="regular@example.com", password="password123", country="NG")
        self.client.force_authenticate(regular_user)
        response = self.client.get(f"/api/admin/hotels/{hotel.id}/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Hotel.objects.count(), 1)
        self.assertEqual(Hotel.objects.get().name, "Test Hotel")
        self.assertEqual(Hotel.objects.get().location, "Test Location")
    def test_admin_can_update_hotel(self):
        """Test that an admin user can update a hotel through the API."""
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.put(f"/api/admin/hotels/{hotel.id}/", data={"name": "Updated Hotel", "location": "Updated Location"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Hotel.objects.get().name, "Updated Hotel")
        self.assertEqual(Hotel.objects.get().location, "Updated Location")
    def test_non_admin_cannot_update_hotel(self):
        """Test that a non-admin user cannot update a hotel through the API."""
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        regular_user = User.objects.create_user(email="regular@example.com", password="password123", country="NG")
        self.client.force_authenticate(regular_user)
        response = self.client.put(f"/api/admin/hotels/{hotel.id}/", data={"name": "Updated Hotel", "location": "Updated Location"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Hotel.objects.get().name, "Test Hotel")
        self.assertEqual(Hotel.objects.get().location, "Test Location")

class AdminHotelViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_admin_can_create_hotel_via_custom_endpoint(self):
        """Test that an admin user can create a hotel using the custom create_hotel endpoint."""
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.post("/api/admin/hotels/custom/", data={"name": "Test Hotel", "location": "Test Location"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Hotel.objects.count(), 1)
        self.assertEqual(Hotel.objects.get().name, "Test Hotel")
        self.assertEqual(Hotel.objects.get().location, "Test Location")
    def test_admin_can_retrieve_hotel_via_custom_endpoint(self):
        """Test that an admin user can retrieve a hotel using the custom get_hotel endpoint."""
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.get(f"/api/admin/hotels/custom/{hotel.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Test Hotel")
        self.assertEqual(response.data["location"], "Test Location")
    def test_admin_can_retrieve_all_hotels_via_custom_endpoint(self):
        """Test that an admin user can retrieve all hotels using the custom get_all_hotels endpoint."""
        Hotel.objects.create(name="Hotel 1", location="Location 1")
        Hotel.objects.create(name="Hotel 2", location="Location 2")
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.get("/api/admin/hotels/custom/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["name"], "Hotel 1")
        self.assertEqual(response.data[0]["location"], "Location 1")
        self.assertEqual(response.data[1]["name"], "Hotel 2")
        self.assertEqual(response.data[1]["location"], "Location 2")

class BookingViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
            country="NG"
        )
        self.other_user = User.objects.create_user(
            email="otheruser@example.com",
            password="password123",
            country="NG"
        )
        BookingEngine.create_booking(
            user=self.user,
            service_type="hotel",
            total_price=Decimal("150.00"),
            currency="NGN",
        )
        BookingEngine.create_booking(
            user=self.other_user,
            service_type="hotel",
            total_price=Decimal("250.00"),
            currency="NGN",
        )
    def test_regular_user_sees_only_own_bookings(self):
        """Test that a regular user can only see their own bookings."""
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["user"],
            self.user.id,
        )
        self.assertEqual(Booking.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Booking.objects.filter(user=self.other_user).count(), 1)
    def test_admin_user_sees_all_bookings(self):
        """Test that an admin user can see all bookings."""
        admin_user = User.objects.create_user(
            email="admin@example.com",
            password="password123",
            country="NG",
            is_staff=True
        )
        self.client.force_authenticate(admin_user)
        response = self.client.get("/api/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        user_ids = {booking["user"] for booking in response.data}
        self.assertIn(self.user.id, user_ids)
        self.assertIn(self.other_user.id, user_ids)
        self.assertEqual(Booking.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Booking.objects.filter(user=self.other_user).count(), 1)

class HotelViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_admin_can_create_hotel(self):
        """Test that an admin user can create a hotel through the API."""
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.post("/api/hotels/", data={
            "name": "Test Hotel",
            "location": "Test Location"
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Hotel.objects.count(), 1)
        self.assertEqual(Hotel.objects.get().name, "Test Hotel")
        self.assertEqual(Hotel.objects.get().location, "Test Location")
    def test_non_admin_cannot_create_hotel(self):
        """Test that a non-admin user cannot create a hotel through the API."""
        regular_user = User.objects.create_user(email="regular@example.com", password="password123", country="NG")
        self.client.force_authenticate(regular_user)
        response = self.client.post("/api/hotels/", data={
            "name": "Test Hotel",
            "location": "Test Location"
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Hotel.objects.count(), 0)
    def test_admin_can_retrieve_hotel(self):
        """Test that an admin user can retrieve a hotel through the API."""
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.get(f"/api/hotels/{hotel.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Test Hotel")
        self.assertEqual(response.data["location"], "Test Location")
    def test_non_admin_can_retrieve_hotel(self):
        """Test that a non-admin user can retrieve a hotel through the API."""
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        regular_user = User.objects.create_user(email="regular@example.com", password="password123", country="NG")
        self.client.force_authenticate(regular_user)
        response = self.client.get(f"/api/hotels/{hotel.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Test Hotel")
        self.assertEqual(response.data["location"], "Test Location")
    def test_admin_can_update_hotel(self):
        """Test that an admin user can update a hotel through the API."""
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.put(f"/api/hotels/{hotel.id}/", data={
            "name": "Updated Hotel",
            "location": "Updated Location"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Hotel.objects.get().name, "Updated Hotel")
        self.assertEqual(Hotel.objects.get().location, "Updated Location")
    def test_non_admin_cannot_update_hotel(self):
        """Test that a non-admin user cannot update a hotel through the API."""
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        regular_user = User.objects.create_user(email="regular@example.com", password="password123", country="NG")
        self.client.force_authenticate(regular_user)
        response = self.client.put(f"/api/hotels/{hotel.id}/", data={
            "name": "Updated Hotel",
            "location": "Updated Location"
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Hotel.objects.get().name, "Test Hotel")
        self.assertEqual(Hotel.objects.get().location, "Test Location")

class AdminHotelViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_admin_can_create_hotel_via_custom_endpoint(self):
        """Test that an admin user can create a hotel using the custom create_hotel endpoint."""
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.post("/api/hotels/create/", data={
            "name": "Test Hotel",
            "location": "Test Location"
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Hotel.objects.count(), 1)
        self.assertEqual(Hotel.objects.get().name, "Test Hotel")
        self.assertEqual(Hotel.objects.get().location, "Test Location")
    def test_admin_can_retrieve_hotel_via_custom_endpoint(self):
        """Test that an admin user can retrieve a hotel using the custom get_hotel endpoint."""
        hotel = Hotel.objects.create(name="Test Hotel", location="Test Location")
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.get(f"/api/hotels/{hotel.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Test Hotel")
        self.assertEqual(response.data["location"], "Test Location")
    def test_admin_can_retrieve_all_hotels_via_custom_endpoint(self):
        """Test that an admin user can retrieve all hotels using the custom get_all_hotels endpoint."""
        Hotel.objects.create(name="Hotel 1", location="Location 1")
        Hotel.objects.create(name="Hotel 2", location="Location 2")
        admin_user = User.objects.create_user(email="admin@example.com", password="password123", country="NG", is_staff=True)
        self.client.force_authenticate(admin_user)
        response = self.client.get("/api/hotels/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["name"], "Hotel 1")
        self.assertEqual(response.data[0]["location"], "Location 1")
        self.assertEqual(response.data[1]["name"], "Hotel 2")
        self.assertEqual(response.data[1]["location"], "Location 2")
        