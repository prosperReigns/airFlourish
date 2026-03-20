from django.contrib import admin
from .models import VisaApplication, VisaDocument, VisaPayment, VisaType

@admin.register(VisaType)
class VisaTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "country", "is_active")
    list_filter = ("country", "is_active")
    search_fields = ("name", "code")

@admin.register(VisaApplication)
class VisaApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "agent",
        "visa_type",
        "status",
        "embassy_review_status",
        "is_locked",
        "created_at",
    )
    list_filter = ("status", "embassy_review_status", "is_locked")


@admin.register(VisaDocument)
class VisaDocumentAdmin(admin.ModelAdmin):
    list_display = ("application", "document_type", "is_verified", "created_at")
    list_filter = ("document_type", "is_verified")


@admin.register(VisaPayment)
class VisaPaymentAdmin(admin.ModelAdmin):
    list_display = ("application", "amount", "currency", "status", "tx_ref", "created_at")
    list_filter = ("status", "currency")
