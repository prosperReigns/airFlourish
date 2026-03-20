from django.db import models
from django.conf import settings

from app.bookings.models import Booking
from app.services.reference_generator import generate_booking_reference


def generate_transport_reference():
    return generate_booking_reference("TRP")

class Trip(models.Model):
    STATUS_CHOICES = (
        ("scheduled", "Scheduled"),
        ("assigned", "Assigned"),
        ("en_route", "En Route"),
        ("arrived", "Arrived"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    name = models.CharField(max_length=150)
    organization = models.CharField(max_length=150, null=True, blank=True)

    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)

    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField(null=True, blank=True)

    # Flight awareness
    flight_number = models.CharField(max_length=50, null=True, blank=True)
    airline = models.CharField(max_length=100, null=True, blank=True)
    expected_arrival_time = models.DateTimeField(null=True, blank=True)

    # Capacity logic
    capacity = models.PositiveIntegerField()
    booked_seats = models.PositiveIntegerField(default=0)

    # Shared vs private
    is_shared = models.BooleanField(default=True)
    price_per_seat = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="NGN")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def has_capacity(self, seats):
        return (self.booked_seats + seats) <= self.capacity

    def __str__(self):
        return f"{self.name} ({self.pickup_location} → {self.dropoff_location})"
    
    class Meta:
        indexes = [
            models.Index(fields=["departure_time"]),
            models.Index(fields=["status"]),
            models.Index(fields=["pickup_location"]),
            models.Index(fields=["dropoff_location"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(capacity__gte=1),
                name="trip_capacity_gte_1",
            ),
        ]
    
class Vehicle(models.Model):
    VEHICLE_TYPES = (
        ("sedan", "Sedan"),
        ("suv", "SUV"),
        ("van", "Van"),
        ("bus", "Bus"),
        ("luxury", "Luxury"),
    )

    vehicle_type = models.CharField(max_length=50, choices=VEHICLE_TYPES)
    plate_number = models.CharField(max_length=50, unique=True)
    capacity = models.PositiveIntegerField()
    provider = models.CharField(max_length=150)

    status = models.CharField(
        max_length=20,
        choices=(("available", "Available"), ("assigned", "Assigned"), ("maintenance", "Maintenance")),
        default="available"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.plate_number} ({self.vehicle_type})"
    
class TripAssignment(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="assignments")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    status = models.CharField(
        max_length=20,
        choices=(("assigned", "Assigned"), ("active", "Active"), ("completed", "Completed")),
        default="assigned"
    )

    class Meta:
        unique_together = ("trip", "vehicle")

class TransportBooking(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="bookings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    booking = models.OneToOneField(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transport_booking",
    )

    passengers = models.PositiveIntegerField(default=1)
    expires_at = models.DateTimeField(null=True, blank=True)

    organization = models.CharField(max_length=150, null=True, blank=True)
    special_requests = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=(
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("checked_in", "Checked In"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ),
        default="pending"
    )
    reference = models.CharField(
        max_length=100,
        unique=True,
        default=generate_transport_reference,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ("trip", "user")
        indexes = [
            models.Index(fields=["trip"]),
            models.Index(fields=["user"]),
            models.Index(fields=["status"]),
            models.Index(fields=["reference"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(passengers__gte=1),
                name="transport_passengers_gte_1",
            ),
        ]
