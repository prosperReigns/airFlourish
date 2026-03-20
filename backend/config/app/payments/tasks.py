import logging
import uuid

from celery import shared_task
from django.core.exceptions import ValidationError
from app.audit.services import log_action
from app.hotels.models import HotelReservation
from app.notifications.services import create_notification
from app.payments.models import Payment
from app.payments.services import PaymentVerificationService
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

logger = logging.getLogger(__name__)

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
    if not visa:
        return
    if visa.status == VisaApplication.STATUS_READY_FOR_SUBMISSION:
        return
    if visa.status == VisaApplication.STATUS_PAID:
        return
    if visa.status != VisaApplication.STATUS_READY_FOR_PAYMENT:
        logger.warning(
            "Visa payment confirmed but application %s is %s",
            visa.id,
            visa.status,
        )
        return
    try:
        visa.transition_to(VisaApplication.STATUS_PAID)
    except ValidationError:
        logger.exception("Visa status transition failed for %s", visa.id)


@shared_task(bind=True, max_retries=3)
def process_successful_payment(self, payment_id):
    payment = None
    try:
        payment_uuid = uuid.UUID(str(payment_id))
        payment = Payment.objects.select_related("booking", "booking__user").get(id=payment_uuid)
        booking = payment.booking
        verification_response, verification_source = (
            PaymentVerificationService.extract_stored_verification(payment)
        )
        if verification_response is None:
            verification_response = FlutterwaveService().verify_payment(payment.tx_ref)
            verification_source = "api"

        verification_result = PaymentVerificationService.apply_verification(
            payment,
            verification_response=verification_response,
            source=verification_source,
            mark_failed_on_gateway_error=True,
        )

        if not verification_result.is_successful:
            BookingEngine.update_status(booking, "failed")
            transaction = get_or_create_transaction(
                booking=booking,
                reference=payment.tx_ref,
                amount=payment.amount,
                currency=payment.currency,
            )
            mark_transaction_failed(transaction, provider_response=payment.raw_response)
            return f"Payment {payment_id} failed verification"

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
