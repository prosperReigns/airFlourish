from django.db import models
from app.bookings.models import Booking
from app.flights.models import FlightBooking

class VisaApplication(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending submission"),           # User just created
        ("verified", "Documents verified"),          # Admin checked docs
        ("submitted", "Submitted to embassy"),      # Sent to embassy
        ("approved", "Approved by embassy"),        # Visa issued
        ("rejected", "Rejected by embassy"),        # Visa rejected
    )

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    flight = models.ForeignKey(
        FlightBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Linked flight booking (optional)",
    )
    destination_country = models.CharField(max_length=100)
    visa_type = models.CharField(max_length=100)
    appointment_date = models.DateField(null=True, blank=True)
    document_status = models.CharField(
        max_length=50, default="pending")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )

    # Documents uploads
    passport_scan = models.FileField(upload_to="visa_documents/passports/", null=True, blank=True)
    photo = models.ImageField(upload_to="visa_documents/photos/", null=True, blank=True)
    supporting_docs = models.FileField(upload_to="visa_documents/supporting/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Track admin action timestamps
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.booking.user.first_name} - {self.destination_country} ({self.visa_type} ({self.status})"
