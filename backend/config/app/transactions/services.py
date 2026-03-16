from decimal import Decimal

from django.db import transaction as db_transaction

from app.audit.services import log_action
from app.notifications.services import create_notification
from app.wallets.models import Wallet
from app.wallets.services import credit_wallet

from .models import Transaction


def get_or_create_transaction(*, booking, reference: str, amount=None, currency=None):
    transaction_type = booking.service_type
    amount_value = Decimal(str(amount if amount is not None else booking.total_price or 0))
    currency_value = currency or booking.currency or "NGN"

    transaction, created = Transaction.objects.get_or_create(
        reference=reference,
        defaults={
            "user": booking.user,
            "amount": amount_value,
            "currency": currency_value,
            "status": "pending",
            "transaction_type": transaction_type,
            "related_booking_id": str(booking.id),
        },
    )

    if not created:
        updates = {}
        if amount is not None and transaction.amount != amount_value:
            updates["amount"] = amount_value
        if currency and transaction.currency != currency_value:
            updates["currency"] = currency_value
        if updates:
            for key, value in updates.items():
                setattr(transaction, key, value)
            transaction.save(update_fields=list(updates.keys()))

    return transaction


def mark_transaction_success(transaction, provider_response=None):
    with db_transaction.atomic():
        transaction = Transaction.objects.select_for_update().get(pk=transaction.pk)
        if transaction.status == "successful":
            return transaction

        transaction.status = "successful"
        if provider_response is not None:
            transaction.provider_response = provider_response
        update_fields = ["status"]
        if provider_response is not None:
            update_fields.append("provider_response")
        transaction.save(update_fields=update_fields)

        wallet, _ = Wallet.objects.get_or_create(user=transaction.user)
        credit_wallet(
            wallet,
            transaction.amount,
            f"Payment received for {transaction.transaction_type} booking ({transaction.reference})",
            transaction,
        )

        create_notification(
            user=transaction.user,
            title="Payment successful",
            message=(
                f"Payment {transaction.reference} of {transaction.amount} "
                f"{transaction.currency} was successful."
            ),
            notification_type="success",
        )

        log_action(
            actor=transaction.user,
            action="payment_successful",
            metadata={"transaction_id": str(transaction.id)},
        )

    return transaction


def mark_transaction_failed(transaction, provider_response=None):
    with db_transaction.atomic():
        transaction = Transaction.objects.select_for_update().get(pk=transaction.pk)
        if transaction.status == "failed":
            return transaction

        transaction.status = "failed"
        if provider_response is not None:
            transaction.provider_response = provider_response
        update_fields = ["status"]
        if provider_response is not None:
            update_fields.append("provider_response")
        transaction.save(update_fields=update_fields)

        create_notification(
            user=transaction.user,
            title="Payment failed",
            message=(
                f"Payment {transaction.reference} of {transaction.amount} "
                f"{transaction.currency} failed."
            ),
            notification_type="error",
        )

        log_action(
            actor=transaction.user,
            action="payment_failed",
            metadata={"transaction_id": str(transaction.id)},
        )

    return transaction
