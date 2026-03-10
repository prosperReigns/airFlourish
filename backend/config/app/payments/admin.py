from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "booking",
        "amount",
        "payment_method",
        "tx_ref",               # updated from transaction_id
        "flutterwave_charge_id", # optional, shows Flutterwave charge ID
        "status",
        "currency",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "payment_method", "currency")
    search_fields = ("tx_ref", "booking__id", "flutterwave_charge_id")
    readonly_fields = ("id", "created_at", "updated_at")