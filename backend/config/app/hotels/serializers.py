from rest_framework import serializers
from .models import HotelReservation, Hotel
from django_countries.serializer_fields import CountryField

class HotelReservationSerializer(serializers.ModelSerializer):
    """Serializer for hotel reservations. This serializer is used for creating and managing hotel reservations. The user field is read-only and will be set to the currently authenticated user when creating a reservation.
    Expected request data for creating a reservation:
    {
        "hotel_id": 1,
        "check_in": "2023-10-01",
        "check_out": "2023-10-05",
        "guests": 2
    }
    """
    class Meta:
        model = HotelReservation
        fields = [
            "id",
            "user",
            "booking",
            "hotel_name",
            "check_in",
            "check_out",
            "guests",
            "status",
            "total_price",
            "hold_expires_at",
            "created_at",
        ]
        read_only_fields = ["user", "hold_expires_at"]

class HotelSerializer(serializers.ModelSerializer):
        """Serializer for hotels. This serializer is used for listing and retrieving hotel information. The country field is represented as a nested object with code and name.
        Expected URL for listing hotels: /hotels/
        Expected URL for retrieving a hotel: /hotels/<hotel_id>/
        """
        country = CountryField()
    
        class Meta:
            model = Hotel
            fields = [
                "id",
                "hotel_name",
                "city",
                "address",
                "country",
                "price_per_night",
                "currency",
                "available_rooms",
                "rooms",
                "images",
                "description",
                "facilities",
                "created_at",
            ]

        def get_country(self, obj):
            """Returns the country information as a nested object with code and name.
            Expected output for the country field:
            {
                "code": "US",
                "name": "United States"
            }
            """
            return {
                "code": str(obj.country.code),
                "name": str(obj.country.name)
            }
