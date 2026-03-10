from rest_framework import serializers
from .models import Booking

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            'id',
            'user',
            'service_type',
            'reference_code',
            'status',
            'total_price',
            'created_at',
        ]
        read_only_fields = ['id', 'user', 'reference_code', 'created_at']
