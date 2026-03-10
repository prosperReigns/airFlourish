from django.db import transaction

from app.bookings.models import Booking
from app.services.amadeus import AmadeusService
from .reference_generator import generate_booking_reference


class BookingEngine:
    @staticmethod
    @transaction.atomic
    def create_booking(
        *, user, service_type: str, total_price, currency="NGN", external_service_id=None, metadata=None
    ):
        """Central booking creation logic."""

        reference_code = generate_booking_reference(service_type)

        booking = Booking.objects.create(
            user=user,
            service_type=service_type,
            reference_code=reference_code,
            total_price=total_price,
            currency=currency,
            status="pending",
        )

        # You can later store metadata in JSONField if needed
        # booking.metadata = metadata
        # booking.save()

        return booking

    @staticmethod
    def update_status(booking, new_status):
        booking.status = new_status
        booking.save()

    @staticmethod
    def attach_payment(booking, new_status, payment_reference=None):
        booking.status = new_status
        if payment_reference:
            booking.external_service_id = payment_reference  # optional
        booking.save()

    @staticmethod
    def cancel_booking(booking, reason=None):
        """
        Cancel a booking safely.
        - Updates booking status
        - Optionally marks payment as refunded or failed
        - Logs a reason if provided
        """
        # Step 1: Update booking status
        booking.status = "cancelled"
        booking.save()

        # Step 2: Handle payment if exists
        try:
            payment = booking.payment  # OneToOne relation
            if payment.status == "successful":
                # You could call your payment gateway refund here
                payment.status = "refunded"  # or "cancelled"
                payment.save()
        except booking.payment.RelatedObjectDoesNotExist:
            pass  # No payment exists yet

        # Optional: store reason in metadata if needed
        if reason:
            # Assuming Booking has a JSONField for metadata
            if hasattr(booking, "metadata") and booking.metadata is not None:
                booking.metadata["cancellation_reason"] = reason
            else:
                booking.metadata = {"cancellation_reason": reason}
            booking.save()

    @staticmethod
    def book_flight(user, flight_offer, travelers, total_price, currency):
        # Step 1: Confirm booking with Amadeus
        amadeus_response = AmadeusService.create_flight_order(
            flight_offer,
            travelers,
        )

        # Step 2: Create unified Booking
        booking = BookingEngine.create_booking(
            user=user,
            service_type="flight",
            total_price=total_price,
            currency=currency,
            external_service_id=amadeus_response.get("id"),
        )
        BookingEngine.update_status(booking, "confirmed")

        return booking, amadeus_response
