from django.utils import timezone
from transport.models import TransportBooking
from app.inventory.services import sync_trip_inventory


def cleanup_expired_bookings():
    expired = TransportBooking.objects.filter(
        status="pending",
        expires_at__lt=timezone.now()
    )

    for booking in expired:
        booking.status = "cancelled"

        trip = booking.trip
        trip.booked_seats -= booking.passengers
        trip.save()

        booking.save()

        sync_trip_inventory(trip.id)