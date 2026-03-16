import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models


class Wallet(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet"
    )

    balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00")
    )

    currency = models.CharField(
        max_length=10,
        default="USD"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} Wallet"
    

class LedgerEntry(models.Model):

    ENTRY_TYPE = [
        ("credit", "Credit"),
        ("debit", "Debit"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="ledger_entries"
    )

    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    entry_type = models.CharField(
        max_length=10,
        choices=ENTRY_TYPE
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    balance_after = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    description = models.CharField(
        max_length=255
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.entry_type} {self.amount}"