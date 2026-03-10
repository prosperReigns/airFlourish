import uuid
from django.db import models
from app.bookings.models import Booking

class Payment(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('booking_failed', 'Booking Failed'),
        ('refunded', 'Refunded'),
    ]

    METHOD_CHOICES = [
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)

    idempotency_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    trace_id = models.CharField(max_length=255, null=True, blank=True)

    tx_ref = models.CharField(max_length=200, unique=True)
    flutterwave_charge_id = models.CharField(max_length=200, null=True, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="NGN")

    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    virtual_account_id = models.CharField(max_length=200, null=True, blank=True)
    payment_method_id = models.CharField(max_length=200, null=True, blank=True)

    raw_response = models.JSONField(null=True, blank=True)  # ✅ ADD THIS
    paid_at = models.DateTimeField(null=True, blank=True)   # ✅ ADD THIS

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.booking} - {self.status}"