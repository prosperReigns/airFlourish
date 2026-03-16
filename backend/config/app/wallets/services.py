from decimal import Decimal
from django.db import transaction
from .models import Wallet, LedgerEntry


def credit_wallet(wallet: Wallet, amount: Decimal, description: str, transaction_obj=None):

    with transaction.atomic():

        wallet.balance += amount
        wallet.save()

        LedgerEntry.objects.create(
            wallet=wallet,
            transaction=transaction_obj,
            entry_type="credit",
            amount=amount,
            balance_after=wallet.balance,
            description=description
        )

    return wallet


def debit_wallet(wallet: Wallet, amount: Decimal, description: str, transaction_obj=None):

    if wallet.balance < amount:
        raise ValueError("Insufficient wallet balance")

    with transaction.atomic():

        wallet.balance -= amount
        wallet.save()

        LedgerEntry.objects.create(
            wallet=wallet,
            transaction=transaction_obj,
            entry_type="debit",
            amount=amount,
            balance_after=wallet.balance,
            description=description
        )

    return wallet