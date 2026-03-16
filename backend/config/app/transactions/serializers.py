from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transaction
        fields = [
            "id",
            "reference",
            "currency",
            "status",
            "transaction_type",
            "created_at"
        ]

        read_only_fields = (
            "id",
            "user",
            "status",
            "provider_response",
            "created_at",
            "updated_at",
        )