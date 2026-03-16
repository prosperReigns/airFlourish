from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from app.wallets.models import Wallet, LedgerEntry
from app.wallets.services import credit_wallet, debit_wallet


class WalletModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="wallet@example.com",
            password="password123",
            country="NG",
        )

    def test_str_includes_user(self):
        wallet = Wallet.objects.create(user=self.user)
        self.assertEqual(str(wallet), f"{self.user} Wallet")

    def test_defaults_balance_and_currency(self):
        wallet = Wallet.objects.create(user=self.user)
        self.assertEqual(wallet.balance, Decimal("0.00"))
        self.assertEqual(wallet.currency, "USD")


class WalletServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="wallet-service@example.com",
            password="password123",
            country="NG",
        )
        self.wallet = Wallet.objects.create(user=self.user)

    def test_credit_wallet_updates_balance_and_creates_ledger(self):
        credit_wallet(self.wallet, Decimal("25.00"), "credit")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("25.00"))
        self.assertEqual(LedgerEntry.objects.filter(wallet=self.wallet).count(), 1)

    def test_debit_wallet_raises_when_insufficient(self):
        with self.assertRaises(ValueError):
            debit_wallet(self.wallet, Decimal("5.00"), "debit")

    def test_debit_wallet_updates_balance_and_creates_ledger(self):
        credit_wallet(self.wallet, Decimal("30.00"), "initial credit")
        debit_wallet(self.wallet, Decimal("10.00"), "debit")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("20.00"))
        self.assertEqual(LedgerEntry.objects.filter(wallet=self.wallet).count(), 2)

    def test_ledger_entry_records_entry_type(self):
        credit_wallet(self.wallet, Decimal("12.00"), "credit")
        entry = LedgerEntry.objects.get(wallet=self.wallet)
        self.assertEqual(entry.entry_type, "credit")
