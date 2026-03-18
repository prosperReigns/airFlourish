import logging

from app.visas.models import VisaPayment

logger = logging.getLogger(__name__)


class IdempotencyConflict(Exception):
    pass


def resolve_payment_idempotency(*, application, amount, currency, key):
    existing = VisaPayment.objects.filter(idempotency_key=key).first()
    if not existing:
        return None

    if (
        existing.application_id != application.id
        or str(existing.amount) != str(amount)
        or existing.currency != currency
    ):
        logger.warning(
            "Visa payment idempotency conflict for key %s (app=%s)",
            key,
            application.id,
        )
        raise IdempotencyConflict(
            "Idempotency-Key reuse with different payload"
        )

    return existing
