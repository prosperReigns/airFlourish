from rest_framework import serializers

from app.bookings.serializers import BookingSerializer
from app.transport.serializers import VehicleSerializer
from .models import CarRental


class CarRentalSerializer(serializers.ModelSerializer):
    vehicle_detail = VehicleSerializer(source="vehicle", read_only=True)
    booking_detail = BookingSerializer(source="booking", read_only=True)

    class Meta:
        model = CarRental
        fields = [
            "id",
            "vehicle",
            "vehicle_detail",
            "user",
            "booking",
            "booking_detail",
            "start_date",
            "end_date",
            "daily_rate",
            "total_price",
            "pickup_location",
            "dropoff_location",
            "deposit_amount",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "user",
            "booking",
            "total_price",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")

        if start and end and end <= start:
            raise serializers.ValidationError("End date must be after start date")

        return attrs
