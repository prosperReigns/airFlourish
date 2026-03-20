from rest_framework import serializers
from .models import Trip, Vehicle, TripAssignment, TransportBooking


class TripSerializer(serializers.ModelSerializer):
    available_seats = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id",
            "name",
            "organization",
            "pickup_location",
            "dropoff_location",
            "departure_time",
            "arrival_time",
            "flight_number",
            "airline",
            "expected_arrival_time",
            "capacity",
            "booked_seats",
            "available_seats",
            "is_shared",
            "price_per_seat",
            "currency",
            "status",
            "created_at",
            "updated_at",
        ]

    def get_available_seats(self, obj):
        return obj.capacity - obj.booked_seats

    def validate_capacity(self, value):
        if value < 1:
            raise serializers.ValidationError("Capacity must be at least 1")
        return value


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            "id",
            "vehicle_type",
            "plate_number",
            "capacity",
            "provider",
            "status",
            "is_active",
        ]


class TripAssignmentSerializer(serializers.ModelSerializer):
    trip_detail = TripSerializer(source="trip", read_only=True)
    vehicle_detail = VehicleSerializer(source="vehicle", read_only=True)

    class Meta:
        model = TripAssignment
        fields = [
            "id",
            "trip",
            "trip_detail",
            "vehicle",
            "vehicle_detail",
            "driver",
            "assigned_at",
            "updated_at",
            "status",
        ]


class TransportBookingSerializer(serializers.ModelSerializer):
    trip_detail = TripSerializer(source="trip", read_only=True)

    class Meta:
        model = TransportBooking
        fields = [
            "id",
            "trip",
            "trip_detail",
            "user",
            "passengers",
            "organization",
            "status",
            "reference",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "user",
            "status",
            "reference",
            "created_at",
            "updated_at",
        ]

    def validate_passengers(self, value):
        if value < 1:
            raise serializers.ValidationError("Passengers must be at least 1")
        return value

    def validate(self, attrs):
        trip = attrs.get("trip")
        passengers = attrs.get("passengers", 1)

        if trip and not trip.has_capacity(passengers):
            raise serializers.ValidationError("Not enough available seats")

        return attrs