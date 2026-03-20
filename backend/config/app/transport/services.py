from django.db import transaction
from .models import Trip, TransportBooking


@transaction.atomic
def create_trip_booking(user, trip_id, passengers, organization=None):
    trip = Trip.objects.select_for_update().get(id=trip_id)

    if not trip.is_shared and trip.booked_seats > 0:
        raise Exception("Private trip already booked")

    if not trip.has_capacity(passengers):
        raise Exception("Not enough available seats")

    booking = TransportBooking.objects.create(
        trip=trip,
        user=user,
        passengers=passengers,
        organization=organization,
        status="pending"
    )

    trip.booked_seats += passengers
    trip.save()

    return booking