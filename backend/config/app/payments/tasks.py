import uuid
from decimal import Decimal, InvalidOperation

from celery import shared_task
from django.utils import timezone

from app.audit.services import log_action
from app.hotels.models import HotelReservation
from app.notifications.services import create_notification
from app.payments.models import Payment
from app.services.booking_engine import BookingEngine
from app.services.flutterwave import FlutterwaveService
from app.services.tasks import process_flight_booking_logic
from app.transactions.services import (
    get_or_create_transaction,
    mark_transaction_failed,
    mark_transaction_success,
)
from app.transport.models import TransportReservation, TransportService
from app.visas.models import VisaApplication

def _confirm_hotel_booking(booking):
    reservation = HotelReservation.objects.filter(booking=booking).first()
    if reservation:
        reservation.status = "confirmed"
        reservation.save(update_fields=["status"])


def _confirm_transport_booking(booking):
    service = TransportService.objects.filter(booking=booking).first()
    if not service:
        return

    passengers_count = service.passengers or 1
    TransportReservation.objects.get_or_create(
        service=service,
        booking=booking,
        defaults={
            "reserved_by": booking.user,
            "passengers_count": passengers_count,
            "special_requests": service.special_requests or "",
            "status": "confirmed",
        },
    )


def _confirm_visa_booking(booking):
    visa = VisaApplication.objects.filter(booking=booking).first()
    if visa:
        visa.status = "submitted"
        visa.save(update_fields=["status"])


@shared_task(bind=True, max_retries=3)
def process_successful_payment(self, payment_id):
    payment = None
    try:
        payment_uuid = uuid.UUID(str(payment_id))
        payment = Payment.objects.select_related("booking", "booking__user").get(id=payment_uuid)
        booking = payment.booking
        raw_response = dict(payment.raw_response or {})
        raw_response.setdefault("meta", raw_response.get("meta") or {})
        verification = raw_response.get("verification")
        if not verification:
            flutterwave_payload = raw_response.get("flutterwave")
            if isinstance(flutterwave_payload, dict) and flutterwave_payload.get("status") == "success":
                verification = flutterwave_payload
        if not verification:
            verification = FlutterwaveService().verify_payment(payment.tx_ref)

        raw_response["verification"] = verification

        if verification.get("status") != "success":
            payment.status = "failed"
            payment.raw_response = raw_response
            payment.save(update_fields=["status", "raw_response"])
            BookingEngine.update_status(booking, "failed")
            transaction = get_or_create_transaction(
                booking=booking,
                reference=payment.tx_ref,
                amount=payment.amount,
                currency=payment.currency,
            )
            mark_transaction_failed(transaction, provider_response=payment.raw_response)
            return f"Payment {payment_id} failed verification"

        verification_data = verification.get("data", {})
        try:
            verified_amount = Decimal(str(verification_data.get("amount")))
        except (InvalidOperation, TypeError):
            verified_amount = None

        if (
            verification_data.get("status") != "successful"
            or verification_data.get("currency") != payment.currency
            or verified_amount is None
            or verified_amount != payment.amount
        ):
            payment.status = "failed"
            payment.raw_response = raw_response
            payment.save(update_fields=["status", "raw_response"])
            BookingEngine.update_status(booking, "failed")
            transaction = get_or_create_transaction(
                booking=booking,
                reference=payment.tx_ref,
                amount=payment.amount,
                currency=payment.currency,
            )
            mark_transaction_failed(transaction, provider_response=payment.raw_response)
            return f"Payment {payment_id} failed verification"

        payment.status = "succeeded"
        if verification_data.get("id"):
            payment.flutterwave_charge_id = str(verification_data.get("id"))
        if payment.paid_at is None:
            payment.paid_at = timezone.now()
        payment.raw_response = raw_response
        payment.save(update_fields=["status", "flutterwave_charge_id", "paid_at", "raw_response"])

        transaction = get_or_create_transaction(
            booking=booking,
            reference=payment.tx_ref,
            amount=payment.amount,
            currency=payment.currency,
        )

        if transaction.status == "successful" and booking.status == "confirmed":
            return f"Payment {payment_id} already processed"

        if booking.service_type == "flight":
            process_flight_booking_logic(payment)
        elif booking.service_type == "hotel":
            _confirm_hotel_booking(booking)
        elif booking.service_type == "transport":
            _confirm_transport_booking(booking)
        elif booking.service_type == "visa":
            _confirm_visa_booking(booking)

        BookingEngine.update_status(booking, "confirmed")
        mark_transaction_success(transaction, provider_response=payment.raw_response)

        create_notification(
            user=booking.user,
            title="Booking confirmed",
            message=f"Your {booking.service_type} booking is confirmed.",
            notification_type="success",
        )

        log_action(
            actor=booking.user,
            action="booking_confirmed",
            metadata={"booking_id": str(booking.id), "service_type": booking.service_type},
        )

        return f"Payment {payment_id} processed"

    except Payment.DoesNotExist:
        return f"Payment {payment_id} does not exist"
    except Exception as exc:
        if payment is not None:
            booking = payment.booking
            payment.status = "booking_failed"
            payment.save(update_fields=["status"])

            BookingEngine.update_status(booking, "failed")
            transaction = get_or_create_transaction(
                booking=booking,
                reference=payment.tx_ref,
                amount=payment.amount,
                currency=payment.currency,
            )
            mark_transaction_failed(transaction, provider_response=payment.raw_response)

            log_action(
                actor=booking.user,
                action="booking_failed",
                metadata={"booking_id": str(booking.id), "service_type": booking.service_type},
            )

        raise self.retry(exc=exc, countdown=60)
