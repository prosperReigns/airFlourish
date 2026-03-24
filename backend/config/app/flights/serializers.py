from rest_framework import serializers
from .models import Airport, FlightBooking

class FlightBookingSerializer(serializers.ModelSerializer):
    """Serializer for flight bookings. This serializer is used for creating and managing flight bookings. The booking field is read-only and will be set to the currently authenticated user's booking when creating a flight booking.
    Expected request data for creating a flight booking:
    {
        "departure_city": "New York",
        "arrival_city": "London",
        "departure_date": "2023-10-01",
        "return_date": "2023-10-10",
        "airline": "British Airways",
        "passengers": 2
    }
    """
    class Meta:
        model = FlightBooking
        fields = [
            'id',
            'booking',
            'departure_city',
            'arrival_city',
            'departure_date',
            'return_date',
            'airline',
            'passengers',
        ]
        read_only_fields = ["booking"]


class AirportSearchSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    value = serializers.CharField(source="code")

    class Meta:
        model = Airport
        fields = ["label", "value"]

    def get_label(self, obj):
        return f"{obj.city} - {obj.name}"


class AirportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ["id", "code", "city", "name", "country"]
