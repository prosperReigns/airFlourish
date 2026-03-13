from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from app.bookings.models import Booking
from app.transport.models import TransportService, TransportReservation
from app.transport.serializers import TransportServiceSerializer, TransportSerializer, TransportReservationSerializer


class TransportFlowTests(TestCase):
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

    def test_user_can_list_available_transports(self):
        TransportService.objects.create(
            vehicle_type="sedan",
            transport_name="Airport Sedan",
            pickup_location="Lagos",
            dropoff_location="Island",
            price_per_passenger=Decimal("50.00"),
            currency="NGN",
        )
        TransportService.objects.create(
            vehicle_type="car_rental",
            transport_name="Daily Car Rental",
            pickup_location="Lagos",
            dropoff_location="Lagos",
            price_per_passenger=Decimal("100.00"),
            currency="NGN",
        )

        self.client.force_authenticate(self.user)
        response = self.client.get("/api/transport/transport-options/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_user_can_book_transport(self):
        transport = TransportService.objects.create(
            vehicle_type="suv",
            transport_name="SUV Ride",
            pickup_location="Lagos",
            dropoff_location="Ikeja",
            price_per_passenger=Decimal("75.00"),
            currency="NGN",
        )

        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/transport/transports/",
            {"transport_id": transport.id, "passengers": 2},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        transport.refresh_from_db()
        self.assertIsNotNone(transport.booking)
        self.assertEqual(transport.passengers, 2)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(transport.booking.user, self.user)

    def test_admin_can_create_transport(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "vehicle_type": "bus",
            "transport_name": "City Bus",
            "pickup_location": "Lagos",
            "dropoff_location": "Abuja",
            "price_per_passenger": "30.00",
            "currency": "NGN",
        }
        response = self.client.post("/api/transport/admin-transports/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(TransportService.objects.count(), 1)
        transport = TransportService.objects.first()
        self.assertEqual(transport.vehicle_type, "bus")
        self.assertEqual(transport.transport_name, "City Bus")
        self.assertEqual(transport.pickup_location, "Lagos")
        self.assertEqual(transport.dropoff_location, "Abuja")
        self.assertEqual(transport.price_per_passenger, Decimal("30.00"))
        self.assertEqual(transport.currency, "NGN")
    def test_user_can_search_transports(self):
        TransportService.objects.create(
            vehicle_type="sedan",
            transport_name="Airport Sedan",
            pickup_location="Lagos",
            dropoff_location="Island",
            price_per_passenger=Decimal("50.00"),
            currency="NGN",
        )
        TransportService.objects.create(
            vehicle_type="car_rental",
            transport_name="Daily Car Rental",
            pickup_location="Lagos",
            dropoff_location="Lagos",
            price_per_passenger=Decimal("100.00"),
            currency="NGN",
        )

        self.client.force_authenticate(self.user)
        response = self.client.get("/api/transport-search/?pickup=Lagos&dropoff=Island&vehicle_type=sedan")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["transport_name"], "Airport Sedan")

class AdminTransportFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="transportadmin@example.com",
            password="password123",
            country="NG",
            user_type="admin",
        )
    def test_admin_can_create_transport(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "vehicle_type": "bus",
            "transport_name": "City Bus",
            "pickup_location": "Lagos",
            "dropoff_location": "Abuja",
            "price_per_passenger": "30.00",
            "currency": "NGN",
        }
        response = self.client.post("/api/transport/admin-transports/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(TransportService.objects.count(), 1)
        transport = TransportService.objects.first()
        self.assertEqual(transport.vehicle_type, "bus")
        self.assertEqual(transport.transport_name, "City Bus")
        self.assertEqual(transport.pickup_location, "Lagos")
        self.assertEqual(transport.dropoff_location, "Abuja")
        self.assertEqual(transport.price_per_passenger, Decimal("30.00"))
        self.assertEqual(transport.currency, "NGN")

class TransportSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
            country="NG",
        )
        TransportService.objects.create(
            vehicle_type="sedan",
            transport_name="Airport Sedan",
            pickup_location="Lagos",
            dropoff_location="Island",
            price_per_passenger=Decimal("50.00"),
            currency="NGN",
        )
        TransportService.objects.create(
            vehicle_type="car_rental",
            transport_name="Daily Car Rental",
            pickup_location="Lagos",
            dropoff_location="Lagos",
            price_per_passenger=Decimal("100.00"),
            currency="NGN",
        )
    def test_user_can_search_transports(self):
        """Test that a regular user can search for transport services based on pickup location, dropoff location, and vehicle type. This test verifies that the search functionality works correctly for regular users and that they can only search for available transport services that are not yet booked."""
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/transport-search/?pickup=Lagos&dropoff=Island&vehicle_type=sedan")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["transport_name"], "Airport Sedan")

class AdminTransportSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="transportadmin@example.com",
            password="password123",
            country="NG",
            user_type="admin",
        )
        TransportService.objects.create(
            vehicle_type="sedan",
            transport_name="Airport Sedan",
            pickup_location="Lagos",
            dropoff_location="Island",
            price_per_passenger=Decimal("50.00"),
            currency="NGN",
        )
        TransportService.objects.create(
            vehicle_type="car_rental",
            transport_name="Daily Car Rental",
            pickup_location="Lagos",
            dropoff_location="Lagos",
            price_per_passenger=Decimal("100.00"),
            currency="NGN",
        )
    def test_admin_can_search_transports(self):
        """Test that an admin user can search for transport services based on pickup location, dropoff location, and vehicle type. This test verifies that the search functionality works correctly for admin users and that they can search through all transport services, including those that are booked and those that are available."""
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/transport-search/?pickup=Lagos&dropoff=Island&vehicle_type=sedan")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["transport_name"], "Airport Sedan")

class TransportBookingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
            country="NG",
        )
        self.transport = TransportService.objects.create(
            vehicle_type="suv",
            transport_name="SUV Ride",
            pickup_location="Lagos",
            dropoff_location="Ikeja",
            price_per_passenger=Decimal("75.00"),
            currency="NGN",
        )
    def test_user_can_book_transport(self):
        """Test that a regular user can book a transport service. This test verifies that the booking process works correctly for regular users and that the booking is associated with the correct user (the regular user in this case)."""
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id, "passengers": 2},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.transport.refresh_from_db()
        self.assertIsNotNone(self.transport.booking)
        self.assertEqual(self.transport.passengers, 2)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(self.transport.booking.user, self.user)

class AdminTransportBookingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="transportadmin@example.com",
            password="password123",
            country="NG",
            user_type="admin",
        )
        self.transport = TransportService.objects.create(
            vehicle_type="suv",
            transport_name="SUV Ride",
            pickup_location="Lagos",
            dropoff_location="Ikeja",
            price_per_passenger=Decimal("75.00"),
            currency="NGN",
        )
    def test_admin_can_book_transport(self):
        """Test that an admin user can book a transport service for themselves or on behalf of another user. This test verifies that the booking process works correctly for admin users and that the booking is associated with the correct user (the admin in this case).
        Expected request data for creating a transport booking:
        {
            "transport_id": 1,
            "passengers": 2
        }
        """
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id, "passengers": 2},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.transport.refresh_from_db()
        self.assertIsNotNone(self.transport.booking)
        self.assertEqual(self.transport.passengers, 2)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(self.transport.booking.user, self.admin)

class TransportListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
            country="NG",
        )
        self.admin = User.objects.create_user(
            email="transportadmin@example.com",
            password="password123",
            country="NG",
            user_type="admin",
        )
        TransportService.objects.create(
            vehicle_type="sedan",
            transport_name="Airport Sedan",
            pickup_location="Lagos",
            dropoff_location="Island",
            price_per_passenger=Decimal("50.00"),
            currency="NGN",
        )
        TransportService.objects.create(
            vehicle_type="car_rental",
            transport_name="Daily Car Rental",
            pickup_location="Lagos",
            dropoff_location="Lagos",
            price_per_passenger=Decimal("100.00"),
            currency="NGN",
        )
    def test_user_can_list_available_transports(self):
        """Test that a regular user can list only available transport services that are not yet booked."""
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/transport/transport-options/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

class AdminTransportListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="transportadmin@example.com",
            password="password123",
            country="NG",
            user_type="admin",
        )
    def test_admin_can_list_available_transports(self):
        """Test that an admin user can list all transport services, including those that are booked and those that are available."""
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/transport/transport-options/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

class TransportDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
            country="NG",
        )
        self.transport = TransportService.objects.create(
            vehicle_type="sedan",
            transport_name="Airport Sedan",
            pickup_location="Lagos",
            dropoff_location="Island",
            price_per_passenger=Decimal("50.00"),
            currency="NGN",
        )
    def test_user_can_retrieve_transport_detail(self):
        """Test that a user can retrieve the details of a specific transport service."""
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/transport/transport-options/{self.transport.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["transport_name"], "Airport Sedan")
        self.assertEqual(response.data["pickup_location"], "Lagos")
        self.assertEqual(response.data["dropoff_location"], "Island")
        self.assertEqual(response.data["price_per_passenger"], "50.00")
        self.assertEqual(response.data["currency"], "NGN")

class AdminTransportDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="transportadmin@example.com",
            password="password123",
            country="NG",
            user_type="admin",
        )
        self.transport = TransportService.objects.create(
            vehicle_type="sedan",
            transport_name="Airport Sedan",
            pickup_location="Lagos",
            dropoff_location="Island",
            price_per_passenger=Decimal("50.00"),
            currency="NGN",
        )
    def test_admin_can_retrieve_transport_detail(self):
        """Test that an admin user can retrieve the details of a specific transport service."""
        self.client.force_authenticate(self.admin)
        response = self.client.get(f"/api/transport/transport-options/{self.transport.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["transport_name"], "Airport Sedan")
        self.assertEqual(response.data["pickup_location"], "Lagos")
        self.assertEqual(response.data["dropoff_location"], "Island")
        self.assertEqual(response.data["price_per_passenger"], "50.00")
        self.assertEqual(response.data["currency"], "NGN")


class TransportModelTests(TestCase):
    def test_transport_service_str_and_defaults(self):
        transport = TransportService.objects.create(
            vehicle_type="sedan",
            transport_name="Model Sedan",
            pickup_location="Lagos",
            dropoff_location="Island",
            price_per_passenger=Decimal("60.00"),
            currency="NGN",
        )
        self.assertEqual(str(transport), "Model Sedan (sedan)")
        self.assertEqual(transport.passengers, 1)


class TransportSerializerTests(TestCase):
    def test_transport_service_serializer_outputs_expected_fields(self):
        transport = TransportService.objects.create(
            vehicle_type="suv",
            transport_name="Serializer SUV",
            pickup_location="Lagos",
            dropoff_location="Ikeja",
            price_per_passenger=Decimal("80.00"),
            currency="NGN",
            passengers=3,
        )
        data = TransportServiceSerializer(transport).data
        self.assertEqual(data["vehicle_type"], "suv")
        self.assertEqual(data["transport_name"], "Serializer SUV")
        self.assertEqual(data["pickup_location"], "Lagos")
        self.assertEqual(data["dropoff_location"], "Ikeja")
        self.assertEqual(data["passengers"], 3)

class TransportSearchSerializerTests(TestCase):
    def test_transport_search_serializer_outputs_expected_fields(self):
        transport = TransportService.objects.create(
            vehicle_type="car_rental",
            transport_name="Search Car Rental",
            pickup_location="Lagos",
            dropoff_location="Lagos",
            price_per_passenger=Decimal("90.00"),
            currency="NGN",
        )
        data = TransportServiceSerializer(transport).data
        self.assertEqual(data["vehicle_type"], "car_rental")
        self.assertEqual(data["transport_name"], "Search Car Rental")
        self.assertEqual(data["pickup_location"], "Lagos")
        self.assertEqual(data["dropoff_location"], "Lagos")
        self.assertEqual(data["price_per_passenger"], "90.00")
        self.assertEqual(data["currency"], "NGN")

class TransportBookingSerializerTests(TestCase):
    def test_transport_booking_serializer_outputs_expected_fields(self):
        transport = TransportService.objects.create(
            vehicle_type="bus",
            transport_name="Booking Bus",
            pickup_location="Lagos",
            dropoff_location="Abuja",
            price_per_passenger=Decimal("40.00"),
            currency="NGN",
            passengers=4,
        )
        data = TransportServiceSerializer(transport).data
        self.assertEqual(data["vehicle_type"], "bus")
        self.assertEqual(data["transport_name"], "Booking Bus")
        self.assertEqual(data["pickup_location"], "Lagos")
        self.assertEqual(data["dropoff_location"], "Abuja")
        self.assertEqual(data["price_per_passenger"], "40.00")
        self.assertEqual(data["currency"], "NGN")

class AdminTransportSerializerTests(TestCase):
    def test_admin_transport_serializer_outputs_expected_fields(self):
        transport = TransportService.objects.create(
            vehicle_type="bus",
            transport_name="Admin Bus",
            pickup_location="Lagos",
            dropoff_location="Abuja",
            price_per_passenger=Decimal("40.00"),
            currency="NGN",
            passengers=4,
        )
        data = TransportServiceSerializer(transport).data
        self.assertEqual(data["vehicle_type"], "bus")
        self.assertEqual(data["transport_name"], "Admin Bus")
        self.assertEqual(data["pickup_location"], "Lagos")
        self.assertEqual(data["dropoff_location"], "Abuja")
        self.assertEqual(data["price_per_passenger"], "40.00")
        self.assertEqual(data["currency"], "NGN")

class TransportSearchResultSerializerTests(TestCase):
    def test_transport_search_result_serializer_outputs_expected_fields(self):
        transport = TransportService.objects.create(
            vehicle_type="sedan",
            transport_name="Search Result Sedan",
            pickup_location="Lagos",
            dropoff_location="Island",
            price_per_passenger=Decimal("50.00"),
            currency="NGN",
        )
        data = TransportServiceSerializer(transport).data
        self.assertEqual(data["vehicle_type"], "sedan")
        self.assertEqual(data["transport_name"], "Search Result Sedan")
        self.assertEqual(data["pickup_location"], "Lagos")
        self.assertEqual(data["dropoff_location"], "Island")
        self.assertEqual(data["price_per_passenger"], "50.00")
        self.assertEqual(data["currency"], "NGN")

class TransportBookingDetailSerializerTests(TestCase):
    def test_transport_booking_detail_serializer_outputs_expected_fields(self):
        transport = TransportService.objects.create(
            vehicle_type="suv",
            transport_name="Booking Detail SUV",
            pickup_location="Lagos",
            dropoff_location="Ikeja",
            price_per_passenger=Decimal("75.00"),
            currency="NGN",
            passengers=2,
        )
        data = TransportServiceSerializer(transport).data
        self.assertEqual(data["vehicle_type"], "suv")
        self.assertEqual(data["transport_name"], "Booking Detail SUV")
        self.assertEqual(data["pickup_location"], "Lagos")
        self.assertEqual(data["dropoff_location"], "Ikeja")
        self.assertEqual(data["price_per_passenger"], "75.00")
        self.assertEqual(data["currency"], "NGN")
        self.assertEqual(data["passengers"], 2)


class TransportSerializerValidationTests(TestCase):
    def test_transport_serializer_missing_required_fields(self):
        serializer = TransportServiceSerializer(
            data={
                "pickup_location": "Lagos",
                "dropoff_location": "Ikeja",
                "price_per_passenger": "80.00",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("vehicle_type", serializer.errors)
        self.assertIn("transport_name", serializer.errors)

    def test_transport_serializer_invalid_price(self):
        serializer = TransportServiceSerializer(
            data={
                "vehicle_type": "suv",
                "transport_name": "Invalid Price",
                "pickup_location": "Lagos",
                "dropoff_location": "Ikeja",
                "price_per_passenger": "not-a-number",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("price_per_passenger", serializer.errors)

class TransportBookingSerializerValidationTests(TestCase):
    def test_transport_booking_serializer_missing_required_fields(self):
        serializer = TransportServiceSerializer(
            data={
                "transport_id": 1,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("passengers", serializer.errors)

    def test_transport_booking_serializer_invalid_passengers(self):
        serializer = TransportServiceSerializer(
            data={
                "transport_id": 1,
                "passengers": "not-a-number",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("passengers", serializer.errors)
        
class TransportAuthTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_transport_list_requires_auth(self):
        response = self.client.get("/api/transport/transport-options/")
        self.assertEqual(response.status_code, 401)

    def test_transport_detail_requires_auth(self):
        response = self.client.get("/api/transport/transport-options/1/")
        self.assertEqual(response.status_code, 401)

    def test_transport_booking_requires_auth(self):
        response = self.client.post("/api/transport/transports/")
        self.assertEqual(response.status_code, 401)

    def test_transport_search_requires_auth(self):
        response = self.client.get("/api/transport-search/")
        self.assertEqual(response.status_code, 401)

    def test_admin_transport_requires_auth(self):
        response = self.client.post("/api/transport/admin-transports/")
        self.assertEqual(response.status_code, 401)

class TransportAdminPermissionTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        User = get_user_model()

        self.user = User.objects.create_user(
            email="user@test.com",
            password="pass",
            country="NG"
        )

    def test_user_cannot_create_transport(self):
        self.client.force_authenticate(self.user)

        payload = {
            "vehicle_type": "bus",
            "transport_name": "Unauthorized Bus",
            "pickup_location": "Lagos",
            "dropoff_location": "Abuja",
            "price_per_passenger": "30.00",
        }

        response = self.client.post("/api/transport/admin-transports/", payload)

        self.assertEqual(response.status_code, 403)

    def test_user_cannot_update_transport(self):
        transport = TransportService.objects.create(
            vehicle_type="bus",
            transport_name="City Bus",
            pickup_location="Lagos",
            dropoff_location="Abuja",
            price_per_passenger="30.00"
        )

        self.client.force_authenticate(self.user)

        response = self.client.patch(
            f"/api/transport/admin-transports/{transport.id}/",
            {"transport_name": "Updated"}
        )

        self.assertEqual(response.status_code, 403)

    def test_user_cannot_delete_transport(self):
        transport = TransportService.objects.create(
            vehicle_type="bus",
            transport_name="City Bus",
            pickup_location="Lagos",
            dropoff_location="Abuja",
            price_per_passenger="30.00"
        )

        self.client.force_authenticate(self.user)

        response = self.client.delete(
            f"/api/transport/admin-transports/{transport.id}/"
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_transport_requires_valid_data(self):
        User = get_user_model()

        admin = User.objects.create_user(
            email="admin@test.com",
            password="pass",
            country="NG",
            user_type="admin"
        )

        self.client.force_authenticate(admin)

        response = self.client.post("/api/transport/admin-transports/", {})

        self.assertEqual(response.status_code, 400)

    def test_admin_can_delete_transport(self):
        User = get_user_model()

        admin = User.objects.create_user(
            email="admin@test.com",
            password="pass",
            country="NG",
            user_type="admin"
        )

        transport = TransportService.objects.create(
            vehicle_type="bus",
            transport_name="City Bus",
            pickup_location="Lagos",
            dropoff_location="Abuja",
            price_per_passenger="30.00"
        )

        self.client.force_authenticate(admin)

        response = self.client.delete(
            f"/api/transport/admin-transports/{transport.id}/"
        )

        self.assertEqual(response.status_code, 204)

class TransportBookingValidationTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        User = get_user_model()

        self.user = User.objects.create_user(
            email="user@test.com",
            password="pass",
            country="NG"
        )

        self.transport = TransportService.objects.create(
            vehicle_type="suv",
            transport_name="SUV Ride",
            pickup_location="Lagos",
            dropoff_location="Ikeja",
            price_per_passenger=Decimal("75.00"),
        )

        self.client.force_authenticate(self.user)

    def test_booking_requires_transport_id(self):
        response = self.client.post(
            "/api/transport/transports/",
            {"passengers": 2},
        )

        self.assertEqual(response.status_code, 400)

    def test_booking_invalid_transport(self):
        response = self.client.post(
            "/api/transport/transports/",
            {"transport_id": 999, "passengers": 2},
        )

        self.assertEqual(response.status_code, 404)

    def test_booking_passengers_default(self):
        response = self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id},
        )

        self.assertEqual(response.status_code, 201)

    def test_booking_passengers_zero(self):
        response = self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id, "passengers": 0},
        )

        self.assertEqual(response.status_code, 400)

    def test_booking_negative_passengers(self):
        response = self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id, "passengers": -2},
        )

        self.assertEqual(response.status_code, 400)

    def test_booking_with_special_requests(self):
        response = self.client.post(
            "/api/transport/transports/",
            {
                "transport_id": self.transport.id,
                "passengers": 2,
                "special_requests": "Need baby seat"
            },
        )

        self.assertEqual(response.status_code, 201)

    def test_booking_sets_special_requests(self):
        response = self.client.post(
            "/api/transport/transports/",
            {
                "transport_id": self.transport.id,
                "special_requests": "VIP service"
            },
        )

        self.transport.refresh_from_db()

        self.assertEqual(self.transport.special_requests, "VIP service")

    def test_booking_total_price_calculation(self):
        response = self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id, "passengers": 3},
        )

        self.assertEqual(response.status_code, 201)

    def test_booking_twice_fails(self):
        self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id}
        )

        response = self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id}
        )

        self.assertEqual(response.status_code, 400)

    def test_booking_creates_booking_object(self):
        self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id}
        )

        self.assertEqual(Booking.objects.count(), 1)

class TransportSearchEdgeTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        User = get_user_model()

        self.user = User.objects.create_user(
            email="user@test.com",
            password="pass",
            country="NG"
        )

        self.client.force_authenticate(self.user)

    def test_search_no_results(self):
        response = self.client.get("/api/transport-search/?pickup=Paris")

        self.assertEqual(len(response.data), 0)

    def test_search_partial_pickup(self):
        TransportService.objects.create(
            vehicle_type="sedan",
            transport_name="Test",
            pickup_location="Lagos Airport",
            dropoff_location="Island",
            price_per_passenger="50"
        )

        response = self.client.get("/api/transport-search/?pickup=Lagos")

        self.assertEqual(len(response.data), 1)

    def test_search_vehicle_type_filter(self):
        TransportService.objects.create(
            vehicle_type="suv",
            transport_name="SUV Test",
            pickup_location="Lagos",
            dropoff_location="Island",
            price_per_passenger="60"
        )

        response = self.client.get("/api/transport-search/?vehicle_type=suv")

        self.assertEqual(len(response.data), 1)

    def test_search_multiple_filters(self):
        TransportService.objects.create(
            vehicle_type="suv",
            transport_name="SUV Test",
            pickup_location="Lagos",
            dropoff_location="Island",
            price_per_passenger="60"
        )

        response = self.client.get(
            "/api/transport-search/?pickup=Lagos&vehicle_type=suv"
        )

        self.assertEqual(len(response.data), 1)

    def test_search_case_insensitive(self):
        TransportService.objects.create(
            vehicle_type="sedan",
            transport_name="Sedan",
            pickup_location="LAGOS",
            dropoff_location="Island",
            price_per_passenger="50"
        )

        response = self.client.get("/api/transport-search/?pickup=lagos")

        self.assertEqual(len(response.data), 1)

class TransportBookingOwnershipTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        User = get_user_model()

        self.user1 = User.objects.create_user(
            email="user1@test.com",
            password="pass",
            country="NG"
        )

        self.user2 = User.objects.create_user(
            email="user2@test.com",
            password="pass",
            country="NG"
        )

        self.transport = TransportService.objects.create(
            vehicle_type="suv",
            transport_name="Ownership Test",
            pickup_location="Lagos",
            dropoff_location="Ikeja",
            price_per_passenger="70"
        )

    def test_user_only_sees_own_booking(self):

        self.client.force_authenticate(self.user1)

        self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id}
        )

        self.client.force_authenticate(self.user2)

        response = self.client.get("/api/transport-bookings/")

        self.assertEqual(len(response.data), 0)

    def test_user_cannot_access_others_booking(self):

        self.client.force_authenticate(self.user1)

        self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id}
        )
        booking_id = Booking.objects.first().id
        self.client.force_authenticate(self.user2)
        response = self.client.get(f"/api/transport-bookings/{booking_id}/")
        self.assertEqual(response.status_code, 404)

    def test_user_cannot_modify_others_booking(self):

        self.client.force_authenticate(self.user1)

        self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id}
        )
        booking_id = Booking.objects.first().id
        self.client.force_authenticate(self.user2)
        response = self.client.patch(f"/api/transport-bookings/{booking_id}/", {"special_requests": "Changed"})
        self.assertEqual(response.status_code, 404)

    def test_user_cannot_delete_others_booking(self):

        self.client.force_authenticate(self.user1)

        self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id}
        )
        booking_id = Booking.objects.first().id
        self.client.force_authenticate(self.user2)
        response = self.client.delete(f"/api/transport-bookings/{booking_id}/")
        self.assertEqual(response.status_code, 404)

class TransportBookingAdminAccessTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        User = get_user_model()

        self.user = User.objects.create_user(
            email="admin@test.com",
            password="pass",
            country="NG",
            is_staff=True
        )
        self.transport = TransportService.objects.create(
            vehicle_type="suv",
            transport_name="Admin Access Test",
            pickup_location="Lagos",
            dropoff_location="Ikeja",
            price_per_passenger="70"
        )
    def test_admin_can_access_all_bookings(self):

        self.client.force_authenticate(self.user)

        self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id}
        )
        booking_id = Booking.objects.first().id
        response = self.client.get(f"/api/transport-bookings/{booking_id}/")
        self.assertEqual(response.status_code, 200)

    def test_admin_can_modify_all_bookings(self):

        self.client.force_authenticate(self.user)

        self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id}
        )
        booking_id = Booking.objects.first().id
        response = self.client.patch(f"/api/transport-bookings/{booking_id}/", {"special_requests": "Admin Changed"})
        self.assertEqual(response.status_code, 200)
        self.transport.refresh_from_db()
        self.assertEqual(self.transport.booking.special_requests, "Admin Changed")

    def test_admin_can_delete_all_bookings(self):

        self.client.force_authenticate(self.user)

        self.client.post(
            "/api/transport/transports/",
            {"transport_id": self.transport.id}
        )
        booking_id = Booking.objects.first().id
        response = self.client.delete(f"/api/transport-bookings/{booking_id}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Booking.objects.count(), 0)

class BaseTransportTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.User = get_user_model()

    def create_user(self, **overrides):
        defaults = {"email": "user@example.com", "password": "password123", "country": "NG"}
        defaults.update(overrides)
        return self.User.objects.create_user(**defaults)

    def create_admin(self, **overrides):
        defaults = {"email": "admin@example.com", "password": "password123", "country": "NG", "user_type": "admin"}
        defaults.update(overrides)
        return self.User.objects.create_user(**defaults)

    def create_transport(self, **overrides):
        defaults = {
            "name": "Test Flight",
            "departure_city": "Lagos",
            "arrival_city": "Abuja",
            "departure_date": date.today() + timedelta(days=1),
            "arrival_date": date.today() + timedelta(days=1, hours=2),
            "available_seats": 5,
            "price_per_seat": Decimal("500.00"),
            "currency": "NGN",
        }
        defaults.update(overrides)
        return Transport.objects.create(**defaults)

    def auth(self, user):
        self.client.force_authenticate(user)


# ---------------------------
# Transport Booking Flow Tests
# ---------------------------
class TransportFlowTests(BaseTransportTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.auth(self.user)
        self.transport = self.create_transport()

    def test_user_can_list_transports(self):
        response = self.client.get("/api/transport/transports/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Test Flight")

    def test_user_can_book_transport(self):
        payload = {"transport_id": self.transport.id, "passengers": 2}
        response = self.client.post("/api/transport/transport-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(TransportReservation.objects.count(), 1)
        self.assertEqual(Booking.objects.count(), 1)
        reservation = TransportReservation.objects.first()
        self.assertEqual(reservation.transport_name, self.transport.name)
        self.assertEqual(reservation.booking.user, self.user)
        self.assertEqual(reservation.total_price, Decimal("1000.00"))  # 2 passengers × 500


# ---------------------------
# Transport Model Tests
# ---------------------------
class TransportModelTests(BaseTransportTestCase):
    def test_transport_str(self):
        transport = self.create_transport(name="Model Flight")
        self.assertEqual(str(transport), "Model Flight")


class TransportReservationModelTests(BaseTransportTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(email="resmodel@example.com")
        self.booking = Booking.objects.create(user=self.user, service_type="transport", reference_code="TRANS-001",
                                              total_price=Decimal("1000.00"), currency="NGN")

    def test_reservation_defaults(self):
        reservation = TransportReservation.objects.create(
            user=self.user, booking=self.booking, transport_name="Model Flight", passengers=2
        )
        self.assertEqual(reservation.status, "pending")
        self.assertEqual(reservation.total_price, Decimal("1000.00"))
        self.assertEqual(reservation.booking, self.booking)


# ---------------------------
# Serializer Tests
# ---------------------------
class TransportSerializerTests(BaseTransportTestCase):
    def test_transport_serializer_outputs_expected_fields(self):
        transport = self.create_transport(name="Serializer Flight")
        data = TransportSerializer(transport).data
        self.assertEqual(data["name"], "Serializer Flight")
        self.assertEqual(data["departure_city"], "Lagos")
        self.assertEqual(data["currency"], "NGN")


class TransportReservationSerializerTests(BaseTransportTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(email="resserializer@example.com")
        self.booking = Booking.objects.create(user=self.user, service_type="transport", reference_code="TRANS-002",
                                              total_price=Decimal("1000.00"), currency="NGN")
        self.reservation = TransportReservation.objects.create(
            user=self.user, booking=self.booking, transport_name="Serializer Flight", passengers=2, total_price=Decimal("1000.00")
        )

    def test_reservation_serializer_fields(self):
        data = TransportReservationSerializer(self.reservation).data
        self.assertEqual(data["user"], self.user.id)
        self.assertEqual(data["booking"], self.booking.id)
        self.assertEqual(data["transport_name"], "Serializer Flight")
        self.assertEqual(data["passengers"], 2)
        self.assertEqual(str(data["total_price"]), "1000.00")


# ---------------------------
# Validation Tests (Booking)
# ---------------------------
class TransportReservationValidationTests(BaseTransportTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(email="resvalidation@example.com")
        self.booking = Booking.objects.create(user=self.user, service_type="transport", reference_code="TRANS-003",
                                              total_price=Decimal("500.00"), currency="NGN")
        self.transport = self.create_transport()

    def test_missing_transport_id(self):
        payload = {"passengers": 1}
        response = self.client.post("/api/transport/transport-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_invalid_passengers_zero(self):
        payload = {"transport_id": self.transport.id, "passengers": 0}
        response = self.client.post("/api/transport/transport-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_passengers_exceed_available_seats(self):
        payload = {"transport_id": self.transport.id, "passengers": 10}
        response = self.client.post("/api/transport/transport-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_booking_nonexistent_transport(self):
        payload = {"transport_id": 99999, "passengers": 1}
        response = self.client.post("/api/transport/transport-reservations/", payload, format="json")
        self.assertEqual(response.status_code, 404)


# ---------------------------
# Access & Permissions Tests
# ---------------------------
class TransportAccessTests(BaseTransportTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(email="user1@example.com")
        self.other_user = self.create_user(email="user2@example.com")
        self.admin = self.create_admin(email="admin@example.com")
        self.transport = self.create_transport()
        self.user_booking = Booking.objects.create(user=self.user, service_type="transport",
                                                   reference_code="TRANS-USER-001", total_price=Decimal("500.00"), currency="NGN")
        self.other_booking = Booking.objects.create(user=self.other_user, service_type="transport",
                                                    reference_code="TRANS-USER-002", total_price=Decimal("500.00"), currency="NGN")
        self.user_reservation = TransportReservation.objects.create(
            user=self.user, booking=self.user_booking, transport_name=self.transport.name, passengers=2, total_price=Decimal("1000.00")
        )
        self.other_reservation = TransportReservation.objects.create(
            user=self.other_user, booking=self.other_booking, transport_name=self.transport.name, passengers=1, total_price=Decimal("500.00")
        )

    def test_user_sees_only_own_reservations(self):
        self.auth(self.user)
        response = self.client.get("/api/transport/transport-reservations/")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.user_reservation.id)

    def test_admin_sees_all_reservations(self):
        self.auth(self.admin)
        response = self.client.get("/api/transport/transport-reservations/")
        self.assertEqual(len(response.data), 2)

    def test_user_cannot_retrieve_other_reservation(self):
        self.auth(self.user)
        response = self.client.get(f"/api/transport/transport-reservations/{self.other_reservation.id}/")
        self.assertEqual(response.status_code, 404)

    def test_user_can_update_own_reservation(self):
        self.auth(self.user)
        response = self.client.patch(f"/api/transport/transport-reservations/{self.user_reservation.id}/",
                                     {"passengers": 3}, format="json")
        self.assertEqual(response.status_code, 200)
        self.user_reservation.refresh_from_db()
        self.assertEqual(self.user_reservation.passengers, 3)

    def test_user_cannot_delete_other_reservation(self):
        self.auth(self.user)
        response = self.client.delete(f"/api/transport/transport-reservations/{self.other_reservation.id}/")
        self.assertEqual(response.status_code, 404)

    def test_user_can_delete_own_reservation(self):
        self.auth(self.user)
        response = self.client.delete(f"/api/transport/transport-reservations/{self.user_reservation.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(TransportReservation.objects.filter(id=self.user_reservation.id).exists())


# ---------------------------
# Edge Case & Concurrency Examples
# ---------------------------
class TransportEdgeTests(BaseTransportTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.auth(self.user)
        self.transport = self.create_transport(available_seats=1)

    def test_concurrent_booking_last_seat(self):
        from threading import Thread

        results = []

        def book():
            payload = {"transport_id": self.transport.id, "passengers": 1}
            res = self.client.post("/api/transport/transport-reservations/", payload, format="json")
            results.append(res.status_code)

        thread1 = Thread(target=book)
        thread2 = Thread(target=book)
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        self.assertIn(201, results)
        self.assertIn(400, results)


# ---------------------------
# Rate Limiting Tests
# ---------------------------
@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": ("app.users.authentication.CustomJWTAuthentication",),
        "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
        "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.UserRateThrottle",),
        "DEFAULT_THROTTLE_RATES": {"user": "1/minute"},
    }
)
class TransportRateLimitingTests(BaseTransportTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.auth(self.user)
        self.transport = self.create_transport()

    def test_rate_limit_transport_list(self):
        first = self.client.get("/api/transport/transports/")
        second = self.client.get("/api/transport/transports/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)

    def test_rate_limit_transport_booking(self):
        payload = {"transport_id": self.transport.id, "passengers": 1}
        first = self.client.post("/api/transport/transport-reservations/", payload, format="json")
        second = self.client.post("/api/transport/transport-reservations/", payload, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 429)

