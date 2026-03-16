from decimal import Decimal
from django.db import transaction
from .models import Wallet, LedgerEntry


def credit_wallet(wallet: Wallet, amount: Decimal, description: str, transaction_obj=None):

    with transaction.atomic():

        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        wallet.balance = wallet.balance + amount
        wallet.save(update_fields=["balance"])

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

    with transaction.atomic():

        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        if wallet.balance < amount:
            raise ValueError(
                f"Insufficient wallet balance (balance={wallet.balance}, requested={amount})"
            )

        wallet.balance = wallet.balance - amount
        wallet.save(update_fields=["balance"])

        LedgerEntry.objects.create(
            wallet=wallet,
            transaction=transaction_obj,
            entry_type="debit",
            amount=amount,
            balance_after=wallet.balance,
            description=description
        )

    return wallet
