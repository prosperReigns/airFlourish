from django.db import models
from app.bookings.models import Booking

class TransportService(models.Model):
    VEHICLE_TYPES = (
        ("sedan", "Sedan"),
        ("suv", "SUV"),
        ("van", "Van"),
        ("bus", "Bus"),
        ("luxury", "Luxury Vehicle"),
        ("car_rental", "Car Rental"),
    )

    # Admin-created transport service
    vehicle_type = models.CharField(max_length=50, choices=VEHICLE_TYPES)
    transport_name = models.CharField(max_length=150)
    pickup_location = models.CharField(max_length=200)
    dropoff_location = models.CharField(max_length=200)
    price_per_passenger = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="NGN")
    created_at = models.DateTimeField(auto_now_add=True)

    # Booking link (set when a user books)
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="transport_details",
        blank=True,
        null=True
    )

    passengers = models.IntegerField(default=1)
    special_requests = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.transport_name} ({self.vehicle_type})"
