from django.contrib import admin
from .models import VisaApplication, VisaDocument, VisaPayment

@admin.register(VisaApplication)
class VisaApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "visa_type",
        "status",
        "is_locked",
        "created_at",
    )
    list_filter = ("status", "is_locked")


@admin.register(VisaDocument)
class VisaDocumentAdmin(admin.ModelAdmin):
    list_display = ("application", "document_type", "is_verified", "created_at")
    list_filter = ("document_type", "is_verified")


@admin.register(VisaPayment)
class VisaPaymentAdmin(admin.ModelAdmin):
    list_display = ("application", "amount", "currency", "status", "tx_ref", "created_at")
    list_filter = ("status", "currency")
