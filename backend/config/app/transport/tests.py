from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from app.bookings.models import Booking
from app.transport.models import TransportService
from app.transport.serializers import TransportServiceSerializer


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
        
