import logging

from app.services.flutterwave import FlutterwaveService
from app.services.reference_generator import generate_booking_reference
from app.visas.models import VisaPayment
from app.visas.services.idempotency_service import resolve_payment_idempotency

logger = logging.getLogger(__name__)


class PaymentInitiationError(Exception):
    pass


def initiate_payment(*, application, amount, currency, idempotency_key, customer_email):
    existing = resolve_payment_idempotency(
        application=application,
        amount=amount,
        currency=currency,
        key=idempotency_key,
    )
    if existing:
        return existing, False

    tx_ref = generate_booking_reference("visa")
    payment_response = FlutterwaveService().initiate_card_payment(
        amount=amount,
        currency=currency,
        customer_email=customer_email,
        tx_ref=tx_ref,
        payment_options="card,banktransfer",
    )

    if payment_response.get("status") == "error":
        logger.error(
            "Visa payment initiation failed: %s",
            payment_response.get("message"),
        )
        raise PaymentInitiationError(payment_response.get("message"))

    payment_link = payment_response.get("data", {}).get("link")
    payment = VisaPayment.objects.create(
        application=application,
        amount=amount,
        currency=currency,
        idempotency_key=idempotency_key,
        tx_ref=tx_ref,
        payment_reference="",
        payment_link=payment_link or "",
        status=VisaPayment.STATUS_PENDING,
    )
    return payment, True
