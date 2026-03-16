import uuid
from django.conf import settings
from django.db import models


class Transaction(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("successful", "Successful"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    TRANSACTION_TYPE = [
        ("flight", "Flight Booking"),
        ("hotel", "Hotel Booking"),
        ("transport", "Transport Booking"),
        ("visa", "Visa Application"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    reference = models.CharField(max_length=200, unique=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    currency = models.CharField(max_length=10)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE
    )

    related_booking_id = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    payment_provider = models.CharField(
        max_length=50,
        default="flutterwave"
    )

    provider_response = models.JSONField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.reference} - {self.status}"