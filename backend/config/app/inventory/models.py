import uuid
from django.db import models


class Inventory(models.Model):

    RESOURCE_TYPES = (
        ("trip", "Trip"),
        ("flight", "Flight"),
        ("hotel", "Hotel"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    provider = models.CharField(max_length=50)

    resource_type = models.CharField(max_length=50, choices=RESOURCE_TYPES)

    # NOW REFERENCES TRIP
    resource_id = models.UUIDField()

    # Time dimension
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    # Route awareness
    pickup_location = models.CharField(max_length=255, null=True, blank=True)
    dropoff_location = models.CharField(max_length=255, null=True, blank=True)

    # Capacity meaning
    available_quantity = models.IntegerField()

    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10)

    metadata = models.JSONField(null=True, blank=True)

    last_synced = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("provider", "resource_id", "start_time")
        indexes = [
            models.Index(fields=["resource_type"]),
            models.Index(fields=["start_time"]),
            models.Index(fields=["pickup_location"]),
            models.Index(fields=["dropoff_location"]),
        ]
        models.CheckConstraint(
            condition=models.Q(available_quantity__gte=0),
            name="available_quantity_non_negative"
        )