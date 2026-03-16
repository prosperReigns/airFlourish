from celery import shared_task
from app.flights.models import FlightBooking
from app.notifications.services import create_notification, send_email
from app.audit.services import log_action
from app.services.booking_engine import BookingEngine

@shared_task
def confirm_flight_booking(booking_id):
    try:
        flight_booking = FlightBooking.objects.select_related("booking", "booking__user").get(id=booking_id)

        BookingEngine.update_status(flight_booking.booking, "confirmed")

        # Send confirmation email
        send_email(
            to=flight_booking.booking.user.email,
            subject="Flight Booking Confirmed",
            body="Your flight booking is confirmed.",
        )

        create_notification(
            user=flight_booking.booking.user,
            title="Flight booking confirmed",
            message="Your flight booking has been confirmed.",
            notification_type="success",
        )

        # Audit log
        log_action(
            actor=flight_booking.booking.user,
            action="flight_booking_confirmed",
            metadata={"booking_id": str(flight_booking.booking.id)},
        )

        return f"Booking {booking_id} confirmed successfully"

    except FlightBooking.DoesNotExist:
        return f"Booking {booking_id} not found"
