from django.conf import settings
from rest_framework import serializers

from .models import VisaApplication, VisaDocument, VisaPayment, VisaType
from .constants import get_default_documents


class VisaTypeField(serializers.SlugRelatedField):
    def to_internal_value(self, data):
        if data in (None, ""):
            return None
        if isinstance(data, dict):
            if "id" in data:
                try:
                    return self.get_queryset().get(id=data["id"])
                except VisaType.DoesNotExist:
                    self.fail("does_not_exist", slug_name="id", value=data["id"])
            if "code" in data:
                value = str(data["code"]).strip()
            elif "name" in data:
                value = str(data["name"]).strip()
            else:
                self.fail("does_not_exist", slug_name=self.slug_field, value=data)
        else:
            value = str(data).strip()

        if value.isdigit():
            try:
                return self.get_queryset().get(id=int(value))
            except VisaType.DoesNotExist:
                pass
        queryset = self.get_queryset()
        try:
            return queryset.get(code__iexact=value)
        except VisaType.DoesNotExist:
            try:
                return queryset.get(name__iexact=value)
            except VisaType.DoesNotExist:
                self.fail("does_not_exist", slug_name=self.slug_field, value=data)


class VisaTypeSerializer(serializers.ModelSerializer):
    def _default_required_documents(self, attrs, instance=None):
        if "required_documents" in attrs and attrs["required_documents"] not in (None, []):
            return attrs["required_documents"]

        defaults = get_default_documents(
            attrs.get("country") if attrs else None,
            attrs.get("name") if attrs else None,
        )
        if not defaults and instance:
            defaults = get_default_documents(instance.country, instance.name or instance.code)
        if defaults:
            return defaults
        return attrs.get("required_documents", [])

    def create(self, validated_data):
        validated_data["required_documents"] = self._default_required_documents(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "required_documents" in validated_data and validated_data["required_documents"] in (None, []):
            validated_data["required_documents"] = self._default_required_documents(validated_data, instance)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        required_documents = data.get("required_documents") or []
        if not required_documents:
            defaults = get_default_documents(instance.country, instance.name or instance.code)
            if defaults:
                data["required_documents"] = defaults
        return data

    class Meta:
        model = VisaType
        fields = [
            "id",
            "code",
            "name",
            "country",
            "description",
            "price",
            "required_documents",
            "processing_days",
            "is_active",
        ]


class VisaApplicationSerializer(serializers.ModelSerializer):
    visa_type = VisaTypeField(
        slug_field="code",
        queryset=VisaType.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    required_documents = serializers.SerializerMethodField()
    visa_type_details = serializers.SerializerMethodField()
    visa_type_price = serializers.SerializerMethodField()
    visa_type_required_documents = serializers.SerializerMethodField()
    visa_type_processing_days = serializers.SerializerMethodField()

    class Meta:
        model = VisaApplication
        fields = [
            "id",
            "user",
            "booking",
            "visa_type",
            "status",
            "is_locked",
            "required_documents",
            "visa_type_details",
            "visa_type_price",
            "visa_type_required_documents",
            "visa_type_processing_days",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "user",
            "booking",
            "status",
            "is_locked",
            "required_documents",
            "visa_type_details",
            "visa_type_price",
            "visa_type_required_documents",
            "visa_type_processing_days",
            "created_at",
            "updated_at",
        ]

    def get_required_documents(self, obj):
        visa_type_docs = []
        if obj.visa_type and isinstance(obj.visa_type.required_documents, list):
            visa_type_docs = obj.visa_type.required_documents
        if visa_type_docs:
            return list(visa_type_docs)

        if obj.visa_type:
            mapped = get_default_documents(obj.visa_type.country, obj.visa_type.name or obj.visa_type.code)
            if mapped:
                return list(mapped)

        required_docs = getattr(settings, "REQUIRED_VISA_DOCUMENT_TYPES", [])
        if isinstance(required_docs, (list, tuple)):
            return list(required_docs)
        return []

    def get_visa_type_details(self, obj):
        if not obj.visa_type:
            return None
        return VisaTypeSerializer(obj.visa_type).data

    def get_visa_type_price(self, obj):
        if not obj.visa_type:
            return None
        return obj.visa_type.price

    def get_visa_type_required_documents(self, obj):
        if not obj.visa_type:
            return []
        if isinstance(obj.visa_type.required_documents, list):
            return obj.visa_type.required_documents
        return []

    def get_visa_type_processing_days(self, obj):
        if not obj.visa_type:
            return None
        return obj.visa_type.processing_days


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

    def validate_document_type(self, value):
        application = self.context.get("application")
        if not application or not application.visa_type:
            return value

        required_docs = []
        visa_type_docs = application.visa_type.required_documents
        if isinstance(visa_type_docs, list):
            required_docs = visa_type_docs

        if not required_docs:
            required_docs = get_default_documents(
                application.visa_type.country, application.visa_type.name or application.visa_type.code
            )

        if required_docs and value not in required_docs:
            raise serializers.ValidationError(
                f"Invalid document type. Allowed: {', '.join(required_docs)}"
            )
        return value


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
