import uuid
from django.db import models


class PricingRule(models.Model):

    RULE_TYPES = (
        ("percentage", "Percentage"),
        ("flat", "Flat Fee"),
    )

    RESOURCE_TYPES = (
        ("flight", "Flight"),
        ("hotel", "Hotel"),
        ("transport", "Transport"),
        ("visa", "Visa"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=100)

    resource_type = models.CharField(
        max_length=50,
        choices=RESOURCE_TYPES
    )

    rule_type = models.CharField(
        max_length=20,
        choices=RULE_TYPES
    )

    value = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    country = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

class ExchangeRate(models.Model):

    base_currency = models.CharField(max_length=10)

    target_currency = models.CharField(max_length=10)

    rate = models.DecimalField(
        max_digits=12,
        decimal_places=6
    )

    updated_at = models.DateTimeField(auto_now=True)