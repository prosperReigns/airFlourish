from celery import shared_task
from django.utils import timezone

from app.audit.services import log_action
from app.notifications.services import create_notification
from app.services.booking_engine import BookingEngine

from .models import HotelReservation


@shared_task
def expire_hotel_reservation_holds():
    now = timezone.now()
    reservations = (
        HotelReservation.objects.select_related("booking", "user")
        .filter(status="pending", hold_expires_at__isnull=False, hold_expires_at__lte=now)
    )
    expired_count = 0
    for reservation in reservations:
        reservation.status = "cancelled"
        reservation.save(update_fields=["status"])
        BookingEngine.update_status(reservation.booking, "cancelled")

        create_notification(
            user=reservation.user,
            title="Reservation expired",
            message="Your hotel reservation hold expired due to non-payment.",
            notification_type="warning",
        )

        log_action(
            actor=reservation.user,
            action="reservation_expired",
            metadata={
                "reservation_id": str(reservation.id),
                "booking_id": str(reservation.booking.id),
                "service_type": "hotel",
            },
        )
        expired_count += 1
    return f"Expired {expired_count} hotel reservations"
