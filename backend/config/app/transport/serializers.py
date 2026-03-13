from rest_framework import serializers
from .models import TransportService, TransportReservation

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
class TransportSerializer(serializers.ModelSerializer):
    """""Serializer for transport reservations. This serializer is used for creating and managing transport reservations related to bookings. It includes all fields of the TransportReservation model and can be used for both creating new transport reservations and updating existing ones.
    Expected request data for creating/updating a transport reservation:
    {
        "service": 1,
        "booking": 1,
        "reserved_by": 1,
        "passengers_count": 2,
        "special_requests": "Need wheelchair access."
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
            "passengers",
            "special_requests",
        ]


class TransportReservationSerializer(serializers.ModelSerializer):
    """Serializer for transport reservations. This serializer is used for creating and managing transport reservations related to bookings. It includes all fields of the TransportReservation model and can be used for both creating new transport reservations and updating existing ones.
    Expected request data for creating/updating a transport reservation:
    {
        "service": 1,
        "booking": 1,
        "reserved_by": 1,
        "passengers_count": 2,
        "special_requests": "Need wheelchair access."
    }
    """
    service_detail = TransportServiceSerializer(source="service", read_only=True)

    class Meta:
        model = TransportReservation
        fields = [
            "id",
            "service",
            "service_detail",
            "booking",
            "reserved_by",
            "passengers_count",
            "special_requests",
            "reserved_at",
            "status",
        ]
        read_only_fields = ["reserved_at", "reserved_by"]