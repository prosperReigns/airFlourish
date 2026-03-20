from django.db import models
from django.conf import settings
import uuid

class Booking(models.Model):
    SERVICE_TYPES = [
        ("flight", "Flight Booking"),
        ("private_jet", "Private Jet Charter"),
        ("visa", "Visa Service"),
        ("hotel", "Hotel Reservation"),
        ("transport", "Transport Service"),
        ("rental", "Car Rental"),
        ("passport", "Passport Renewal"),
        ("protocol", "Airport Protocol"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES)
    reference_code = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=30, default='pending', choices=STATUS_CHOICES)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    external_service_id = models.CharField(max_length=100, null=True, blank=True)
    currency = models.CharField(max_length=10, default='NGN')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.reference_code} - {self.service_type}"

class BookingLock(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    resource_type = models.CharField(
        max_length=50
    )

    resource_id = models.CharField(
        max_length=255
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("resource_type", "resource_id")
