import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from app.payments.utils import sanitize_flutterwave_payload

logger = logging.getLogger(__name__)


@dataclass
class PaymentVerificationResult:
    payment: object
    verification: dict
    normalized_verification: dict
    is_successful: bool
    gateway_error: bool
    failure_reason: str | None


def merge_payment_metadata(
    payment,
    *,
    meta_update=None,
    flutterwave_payload=None,
    verification_payload=None,
):
    raw_response = dict(payment.raw_response or {})
    raw_response.setdefault("meta", {})
    if meta_update:
        raw_response["meta"].update(meta_update)
    if flutterwave_payload is not None:
        raw_response["flutterwave"] = sanitize_flutterwave_payload(flutterwave_payload)
    if verification_payload is not None:
        raw_response["verification"] = sanitize_flutterwave_payload(verification_payload)
    return raw_response


def normalize_verification_payload(payload, source):
    if source == "webhook":
        return {"status": "success", "data": payload or {}}
    if isinstance(payload, dict):
        return payload
    return {}


def parse_verification_amount(amount, tx_ref=None):
    try:
        return Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        if tx_ref:
            escaped_tx_ref = str(tx_ref).replace("\n", "\\n").replace("\r", "\\r")
            logger.warning(
                "Payment verification amount parse failed for tx_ref=%s", escaped_tx_ref
            )
        return None


class PaymentVerificationService:
    @staticmethod
    def extract_stored_verification(payment):
        raw_response = payment.raw_response or {}
        verification = raw_response.get("verification")
        if isinstance(verification, dict):
            return verification, "api"
        flutterwave_payload = raw_response.get("flutterwave")
        if isinstance(flutterwave_payload, dict):
            return flutterwave_payload, "webhook"
        return None, None

    @staticmethod
    def apply_verification(
        payment,
        *,
        verification_response,
        source,
        mark_failed_on_gateway_error=False,
        meta_update=None,
    ):
        normalized = normalize_verification_payload(verification_response, source)
        raw_response = merge_payment_metadata(
            payment,
            meta_update=meta_update,
            flutterwave_payload=verification_response if source == "webhook" else None,
            verification_payload=normalized,
        )

        gateway_error = normalized.get("status") != "success"
        if gateway_error:
            if mark_failed_on_gateway_error:
                payment.status = "failed"
                payment.raw_response = raw_response
                payment.save(update_fields=["status", "raw_response"])
            return PaymentVerificationResult(
                payment=payment,
                verification=verification_response,
                normalized_verification=normalized,
                is_successful=False,
                gateway_error=True,
                failure_reason="verification_failed",
            )

        verification_data = normalized.get("data", {})
        if not isinstance(verification_data, dict):
            verification_data = {}

        verified_amount = parse_verification_amount(
            verification_data.get("amount"), tx_ref=payment.tx_ref
        )

        if (
            verification_data.get("status") != "successful"
            or verification_data.get("currency") != payment.currency
            or verified_amount is None
            or verified_amount != payment.amount
        ):
            payment.status = "failed"
            payment.raw_response = raw_response
            payment.save(update_fields=["status", "raw_response"])
            return PaymentVerificationResult(
                payment=payment,
                verification=verification_response,
                normalized_verification=normalized,
                is_successful=False,
                gateway_error=False,
                failure_reason="verification_mismatch",
            )

        payment.status = "succeeded"
        if verification_data.get("id"):
            payment.flutterwave_charge_id = str(verification_data.get("id"))
        if payment.paid_at is None:
            payment.paid_at = timezone.now()
        payment.raw_response = raw_response
        update_fields = ["status", "raw_response", "paid_at"]
        if verification_data.get("id"):
            update_fields.append("flutterwave_charge_id")
        payment.save(update_fields=update_fields)

        return PaymentVerificationResult(
            payment=payment,
            verification=verification_response,
            normalized_verification=normalized,
            is_successful=True,
            gateway_error=False,
            failure_reason=None,
        )
