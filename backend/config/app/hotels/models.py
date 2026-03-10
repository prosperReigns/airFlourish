from django.conf import settings
from django.db import models
from django_countries.fields import CountryField

from app.bookings.models import Booking


class HotelReservation(models.Model):
    STATUS = (
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hotel_reservations",
    )

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="hotel_reservations",
    )
    hotel_name = models.CharField(max_length=150)
    check_in = models.DateField()
    check_out = models.DateField()

    guests = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="pending",
    )
    total_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.hotel_name}"


class Hotel(models.Model):
    hotel_name = models.CharField(max_length=150)
    city = models.CharField(max_length=100)
    address = models.TextField(blank=True, null=True)
    country = CountryField()

    price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    currency = models.CharField(max_length=10, default="NGN")

    available_rooms = models.PositiveIntegerField(default=1)
    rooms = models.JSONField(blank=True, null=True)
    images = models.JSONField(blank=True, null=True)

    description = models.TextField(blank=True, null=True)
    facilities = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.hotel_name
