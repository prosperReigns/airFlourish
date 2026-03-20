from django.db import models
from django.conf import settings

from app.bookings.models import Booking

class CarRental(models.Model):
    vehicle = models.ForeignKey("transport.Vehicle", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    booking = models.OneToOneField(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="car_rental",
    )

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255, null=True, blank=True)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=(("pending", "Pending"), ("confirmed", "Confirmed"), ("active", "Active"), ("completed", "Completed"), ("cancelled", "Cancelled")),
        default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        indexes = [
            models.Index(fields=["start_date"]),
            models.Index(fields=["end_date"]),
            models.Index(fields=["vehicle"]),
            models.Index(fields=["user"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gt=models.F("start_date")),
                name="rental_end_date_after_start_date",
            ),
        ]
