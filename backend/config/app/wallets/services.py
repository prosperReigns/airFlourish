from decimal import Decimal
from django.db import transaction
from .models import Wallet, LedgerEntry


def credit_wallet(wallet: Wallet, amount: Decimal, description: str, transaction_obj=None):

    with transaction.atomic():

        locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        locked_wallet.balance = locked_wallet.balance + amount
        locked_wallet.save(update_fields=["balance"])

        LedgerEntry.objects.create(
            wallet=locked_wallet,
            transaction=transaction_obj,
            entry_type="credit",
            amount=amount,
            balance_after=locked_wallet.balance,
            description=description
        )

    wallet.refresh_from_db()
    return wallet


def debit_wallet(wallet: Wallet, amount: Decimal, description: str, transaction_obj=None):

    with transaction.atomic():

        locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        if locked_wallet.balance < amount:
            raise ValueError(
                f"Insufficient wallet balance (balance={locked_wallet.balance}, requested={amount})"
            )

        locked_wallet.balance = locked_wallet.balance - amount
        locked_wallet.save(update_fields=["balance"])

        LedgerEntry.objects.create(
            wallet=locked_wallet,
            transaction=transaction_obj,
            entry_type="debit",
            amount=amount,
            balance_after=locked_wallet.balance,
            description=description
        )

    wallet.refresh_from_db()
    return wallet
