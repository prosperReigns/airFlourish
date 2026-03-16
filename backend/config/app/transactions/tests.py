from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from app.services.booking_engine import BookingEngine
from app.transactions.services import get_or_create_transaction, mark_transaction_success
from app.wallets.models import LedgerEntry, Wallet


class TransactionServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="transaction@example.com",
            password="password123",
            country="NG",
        )

    def test_mark_transaction_success_idempotent(self):
        booking = BookingEngine.create_booking(
            user=self.user,
            service_type="hotel",
            total_price=Decimal("150.00"),
            currency="NGN",
        )
        transaction = get_or_create_transaction(
            booking=booking,
            reference="tx-idempotent-001",
            amount=Decimal("150.00"),
            currency="NGN",
        )

        mark_transaction_success(transaction)
        mark_transaction_success(transaction)

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal("150.00"))
        self.assertEqual(
            LedgerEntry.objects.filter(wallet=wallet, transaction=transaction).count(),
            1,
        )
