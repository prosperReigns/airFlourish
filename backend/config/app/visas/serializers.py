from rest_framework import serializers
from .models import VisaApplication

class VisaApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaApplication
        fields = [
            "id",
            "booking",
            "flight",
            "destination_country",
            "visa_type",
            "appointment_date",
            "document_status",
            "status",
            "passport_scan",
            "photo",
            "supporting_docs",
            "created_at",
            "updated_at",
            "reviewed_at",
            "approved_at",
            "rejected_at",
        ]
        read_only_fields = ["booking", "document_status", "created_at", "updated_at"]
