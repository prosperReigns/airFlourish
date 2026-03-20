from rest_framework import serializers
from .models import Inventory


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = [
            "id",
            "provider",
            "resource_type",
            "resource_id",
            "start_time",
            "end_time",
            "pickup_location",
            "dropoff_location",
            "available_quantity",
            "price",
            "currency",
            "metadata",
            "last_synced",
            "updated_at",
        ]

    def validate_available_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative")
        return value

    def validate(self, attrs):
        start = attrs.get("start_time")
        end = attrs.get("end_time")

        if start and end and end <= start:
            raise serializers.ValidationError("End time must be after start time")

        return attrs