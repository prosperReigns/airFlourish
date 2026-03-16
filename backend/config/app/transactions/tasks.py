from celery import shared_task
from django.utils import timezone
from .models import Transaction 
from app.wallets.models import Wallet, LedgerEntry
from app.audit.models import AuditLog
#from app.notifications.services import send_email

@shared_task(bind=True, max_retries=3)
def process_payment(self, transaction_id):
    try:
        transaction = Transaction.objects.get(id=transaction_id)

        # Simulate payment verification with Flutterwave API
        result = {"status": "success"}  # replace with real API call

        if result["status"] == "success":
            transaction.status = "completed"
            transaction.save()

            # Update user wallet
            wallet, _ = Wallet.objects.get_or_create(user=transaction.user)
            wallet.balance += transaction.amount
            wallet.save()

            # Ledger entry
            LedgerEntry.objects.create(
                transaction=transaction,
                user=transaction.user,
                amount=transaction.amount,
                description=f"Payment received, ref: {transaction.reference}"
            )

            # Audit log
            AuditLog.objects.create(
                actor=transaction.user,
                action="Payment processed",
                metadata={"transaction_id": transaction.id, "amount": str(transaction.amount)}
            )

            # Send confirmation email
            send_email(
                to=transaction.user.email,
                subject="Payment Successful",
                body=f"Your payment of {transaction.amount} has been successfully processed."
            )

        else:
            transaction.status = "failed"
            transaction.save()
            AuditLog.objects.create(
                actor=transaction.user,
                action="Payment failed",
                metadata={"transaction_id": transaction.id}
            )

        return f"Transaction {transaction_id} processed"

    except Transaction.DoesNotExist:
        return f"Transaction {transaction_id} does not exist"