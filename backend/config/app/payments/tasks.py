from celery import shared_task
from app.payments.models import Payment
from app.transactions.services import record_transaction
from app.audit.services import log_action

@shared_task(bind=True, max_retries=3)
def verify_payment(self, payment_id):
    try:
        payment = Payment.objects.get(id=payment_id)

        # Check with Flutterwave API
        result = payment.verify()  # your method calling Flutterwave

        if result["status"] == "success":
            payment.status = "completed"
            payment.save()

            # Record transaction in ledger
            record_transaction(
                user=payment.user,
                amount=payment.amount,
                reference=payment.reference
            )

            log_action(
                actor=payment.user,
                action="payment verified",
                metadata={"payment_id": payment_id}
            )
        else:
            payment.status = "failed"
            payment.save()

        return result

    except Payment.DoesNotExist:
        return f"Payment {payment_id} does not exist"