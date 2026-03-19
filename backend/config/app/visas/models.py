from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from app.bookings.models import Booking
from app.visas.constants import get_default_documents


class VisaType(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=2, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    required_documents = models.JSONField(default=list, blank=True)
    processing_days = models.PositiveIntegerField(default=7)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["country", "is_active"])]

    def save(self, *args, **kwargs):
        if not self.required_documents:
            defaults = get_default_documents(self.country, self.name or self.code)
            if defaults:
                self.required_documents = defaults
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"


class VisaApplication(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_INCOMPLETE = "incomplete"
    STATUS_READY_FOR_PAYMENT = "ready_for_payment"
    STATUS_PAID = "paid"
    STATUS_SUBMITTED = "submitted"
    STATUS_UNDER_REVIEW = "under_review"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_INCOMPLETE, "Incomplete"),
        (STATUS_READY_FOR_PAYMENT, "Ready for payment"),
        (STATUS_PAID, "Paid"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_UNDER_REVIEW, "Under review"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    )

    ALLOWED_TRANSITIONS = {
        STATUS_DRAFT: {STATUS_INCOMPLETE, STATUS_READY_FOR_PAYMENT},
        STATUS_INCOMPLETE: {STATUS_READY_FOR_PAYMENT},
        STATUS_READY_FOR_PAYMENT: {STATUS_PAID},
        STATUS_PAID: {STATUS_SUBMITTED},
        STATUS_SUBMITTED: {STATUS_UNDER_REVIEW},
        STATUS_UNDER_REVIEW: {STATUS_APPROVED, STATUS_REJECTED},
        STATUS_APPROVED: set(),
        STATUS_REJECTED: set(),
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="visa_applications",
    )
    booking = models.OneToOneField(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visa_application",
    )
    visa_type = models.ForeignKey(
        VisaType,
        on_delete=models.PROTECT,
        related_name="applications",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def transition_to(self, new_status):
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError(
                f"Cannot transition from {self.status} to {new_status}"
            )
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])

    def lock(self):
        if not self.is_locked:
            self.is_locked = True
            self.save(update_fields=["is_locked", "updated_at"])

    def __str__(self):
        visa_type = self.visa_type.name if self.visa_type else "unknown"
        return f"{self.user_id} - {visa_type} ({self.status})"


class VisaDocument(models.Model):
    application = models.ForeignKey(
        VisaApplication,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=100)
    file = models.FileField(upload_to="visa_documents/")
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application_id} - {self.document_type}"


class VisaPayment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SUCCESSFUL = "successful"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESSFUL, "Successful"),
        (STATUS_FAILED, "Failed"),
    )

    application = models.ForeignKey(
        VisaApplication,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    idempotency_key = models.CharField(max_length=255, unique=True)
    tx_ref = models.CharField(max_length=100)
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_link = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["tx_ref"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.application_id} - {self.status}"
