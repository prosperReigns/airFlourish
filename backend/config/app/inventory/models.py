import uuid
from django.db import models


class Inventory(models.Model):

    RESOURCE_TYPES = (
        ("flight", "Flight"),
        ("hotel", "Hotel"),
        ("transport", "Transport"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    provider = models.CharField(max_length=50)

    resource_type = models.CharField(
        max_length=50,
        choices=RESOURCE_TYPES
    )

    resource_id = models.CharField(max_length=255)

    available_quantity = models.IntegerField()

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    currency = models.CharField(max_length=10)

    metadata = models.JSONField(null=True, blank=True)

    last_synced = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("provider", "resource_id")