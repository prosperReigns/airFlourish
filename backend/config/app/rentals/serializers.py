from rest_framework import serializers
from .models import CarRental


class CarRentalSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarRental
        fields = [
            "id",
            "vehicle",
            "user",
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
        read_only_fields = ["user", "total_price", "status"]

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")

        if start and end and end <= start:
            raise serializers.ValidationError("End date must be after start date")

        return attrs