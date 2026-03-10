from rest_framework import serializers
from .models import TransportService

class TransportServiceSerializer(serializers.ModelSerializer):
    """Serializer for transport services. This serializer is used for creating and managing transport services related to bookings. It includes all fields of the TransportService model and can be used for both creating new transport services and updating existing ones.
    Expected request data for creating/updating a transport service:
    {
        "booking": 1,
        "transport_type": "car",
        "pickup_location": "123 Main St, City",
        "dropoff_location": "456 Elm St, City",
        "pickup_time": "2023-10-01T10:00:00Z",
        "dropoff_time": "2023-10-01T12:00:00Z",
        "company": "Transport Co",
        "price": 50.00,
        "currency": "USD"
    }
    """
    class Meta:
        model = TransportService
        fields = [
            "id",
            "vehicle_type",
            "transport_name",
            "pickup_location",
            "dropoff_location",
            "price_per_passenger",
            "currency",
            "created_at",
            "booking",
            "passengers",
            "special_requests",
        ]
