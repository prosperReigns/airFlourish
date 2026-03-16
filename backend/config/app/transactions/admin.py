from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):

    list_display = (
        "reference",
        "user",
        "amount",
        "currency",
        "status",
        "transaction_type",
        "created_at",
    )

    search_fields = ("reference", "user__email")

    list_filter = ("status", "transaction_type", "currency")

    readonly_fields = (
        "reference",
        "provider_response",
        "created_at",
        "updated_at",
    )