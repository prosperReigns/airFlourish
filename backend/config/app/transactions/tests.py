from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from app.services.booking_engine import BookingEngine
from app.transactions.models import Transaction
from app.transactions.serializers import TransactionSerializer
from app.transactions.services import (
    get_or_create_transaction,
    mark_transaction_failed,
    mark_transaction_success,
)
from app.wallets.models import LedgerEntry, Wallet


class TransactionServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="transaction@example.com",
            password="password123",
            country="NG",
        )

    def test_mark_transaction_success_prevents_duplicate_wallet_credits(self):
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

    def test_get_or_create_transaction_updates_amount_and_currency(self):
        booking = BookingEngine.create_booking(
            user=self.user,
            service_type="hotel",
            total_price=Decimal("100.00"),
            currency="NGN",
        )
        transaction = get_or_create_transaction(
            booking=booking,
            reference="tx-update-001",
            amount=Decimal("100.00"),
            currency="NGN",
        )
        updated = get_or_create_transaction(
            booking=booking,
            reference="tx-update-001",
            amount=Decimal("125.00"),
            currency="USD",
        )
        transaction.refresh_from_db()
        updated.refresh_from_db()
        self.assertEqual(transaction.id, updated.id)
        self.assertEqual(updated.amount, Decimal("125.00"))
        self.assertEqual(updated.currency, "USD")

    def test_mark_transaction_failed_sets_status(self):
        booking = BookingEngine.create_booking(
            user=self.user,
            service_type="transport",
            total_price=Decimal("80.00"),
            currency="NGN",
        )
        transaction = get_or_create_transaction(
            booking=booking,
            reference="tx-fail-001",
            amount=Decimal("80.00"),
            currency="NGN",
        )
        mark_transaction_failed(transaction, provider_response={"status": "failed"})
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, "failed")
        self.assertEqual(transaction.provider_response, {"status": "failed"})


class TransactionModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="transaction-model@example.com",
            password="password123",
            country="NG",
        )

    def test_str_includes_reference_and_status(self):
        transaction = Transaction.objects.create(
            user=self.user,
            reference="tx-model-001",
            amount=Decimal("50.00"),
            currency="NGN",
            transaction_type="flight",
        )
        self.assertEqual(str(transaction), "tx-model-001 - pending")

    def test_defaults_set(self):
        transaction = Transaction.objects.create(
            user=self.user,
            reference="tx-model-002",
            amount=Decimal("75.00"),
            currency="NGN",
            transaction_type="hotel",
        )
        self.assertEqual(transaction.status, "pending")
        self.assertEqual(transaction.payment_provider, "flutterwave")

    def test_transaction_type_saved(self):
        transaction = Transaction.objects.create(
            user=self.user,
            reference="tx-model-003",
            amount=Decimal("30.00"),
            currency="NGN",
            transaction_type="visa",
        )
        self.assertEqual(transaction.transaction_type, "visa")


class TransactionSerializerTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="transaction-serializer@example.com",
            password="password123",
            country="NG",
        )
        self.transaction = Transaction.objects.create(
            user=self.user,
            reference="tx-serial-001",
            amount=Decimal("60.00"),
            currency="NGN",
            transaction_type="flight",
        )

    def test_serializer_outputs_expected_fields(self):
        data = TransactionSerializer(self.transaction).data
        self.assertEqual(data["reference"], "tx-serial-001")
        self.assertEqual(data["currency"], "NGN")
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["transaction_type"], "flight")
        self.assertIn("created_at", data)
