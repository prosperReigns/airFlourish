from rest_framework import serializers

from .models import VisaApplication, VisaDocument, VisaPayment


class VisaApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaApplication
        fields = [
            "id",
            "user",
            "booking",
            "visa_type",
            "status",
            "is_locked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "user",
            "booking",
            "status",
            "is_locked",
            "created_at",
            "updated_at",
        ]


class VisaDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaDocument
        fields = [
            "id",
            "application",
            "document_type",
            "file",
            "is_verified",
            "created_at",
        ]
        read_only_fields = ["application", "is_verified", "created_at"]


class VisaPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaPayment
        fields = [
            "id",
            "application",
            "amount",
            "currency",
            "status",
            "idempotency_key",
            "tx_ref",
            "payment_reference",
            "payment_link",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "application",
            "status",
            "tx_ref",
            "payment_reference",
            "payment_link",
            "created_at",
            "updated_at",
        ]
