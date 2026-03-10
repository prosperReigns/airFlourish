from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment processing. This serializer is used for creating and managing payments related to bookings. The status, paid_at, and created_at fields are read-only and will be set automatically based on the payment processing results.
    Expected request data for creating a payment:
    {
        "booking": 1,"
        "amount": 100.00,
        "currency": "USD",
        "payment_method": "card",
        "tx_ref": "unique_transaction_reference"
    }
    """
    class Meta:
        model = Payment
        fields = [
            'id',
            'booking',
            'amount',
            'currency',
            'payment_method',
            'tx_ref',
            'status',
            'paid_at',
            'created_at'
        ]
        read_only_fields = ['status', 'paid_at', 'created_at']