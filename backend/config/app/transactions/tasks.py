from celery import shared_task

from .models import Transaction
from .services import mark_transaction_failed, mark_transaction_success

@shared_task(bind=True, max_retries=3)
def process_payment(self, transaction_id):
    try:
        transaction = Transaction.objects.get(id=transaction_id)

        # Simulate payment verification with Flutterwave API
        result = {"status": "success"}  # replace with real API call

        if result["status"] == "success":
            mark_transaction_success(transaction, provider_response=result)
        else:
            mark_transaction_failed(transaction, provider_response=result)

        return f"Transaction {transaction_id} processed"

    except Transaction.DoesNotExist:
        return f"Transaction {transaction_id} does not exist"
