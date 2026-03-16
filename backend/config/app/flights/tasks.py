from celery import shared_task
from django.utils import timezone
from app.bookings.models import FlightBooking
from app.notifications.services import send_email
from app.audit.services import log_action

@shared_task
def confirm_flight_booking(booking_id):
    try:
        booking = FlightBooking.objects.get(id=booking_id)

        # Simulate API call to Sabre or ticket issuance
        booking.status = "confirmed"
        booking.confirmed_at = timezone.now()
        booking.save()

        # Send confirmation email
        send_email(
            to=booking.user.email,
            subject="Flight Booking Confirmed",
            body=f"Your flight {booking.flight_number} is confirmed!"
        )

        # Audit log
        log_action(
            actor=booking.user,
            action="flight booking confirmed",
            metadata={"booking_id": booking_id}
        )

        return f"Booking {booking_id} confirmed successfully"

    except FlightBooking.DoesNotExist:
        return f"Booking {booking_id} not found"