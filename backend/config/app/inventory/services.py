from .models import Inventory
from transport.models import Trip
from django.db import transaction

def update_inventory(provider, resource_id, quantity, price, currency):

    inventory, created = Inventory.objects.update_or_create(
        provider=provider,
        resource_id=resource_id,
        defaults={
            "available_quantity": quantity,
            "price": price,
            "currency": currency
        }
    )

    return inventory


@transaction.atomic
def sync_trip_inventory(trip_id):
    trip = Trip.objects.select_for_update().get(id=trip_id)

    available = trip.capacity - trip.booked_seats

    Inventory.objects.update_or_create(
        provider="internal",
        resource_id=str(trip.id),
        defaults={
            "resource_type": "trip",
            "available_quantity": available,
            "price": 0,  # optional if dynamic
            "currency": "NGN",
            "start_time": trip.departure_time,
            "end_time": trip.arrival_time,
            "pickup_location": trip.pickup_location,
            "dropoff_location": trip.dropoff_location,
            "metadata": {
                "capacity": trip.capacity,
                "booked": trip.booked_seats,
                "is_shared": trip.is_shared
            }
        }
    )