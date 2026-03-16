from django.contrib import admin
from .models import Wallet, LedgerEntry


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "balance",
        "currency",
        "is_active",
        "created_at"
    )

    search_fields = ("user__email",)


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):

    list_display = (
        "wallet",
        "entry_type",
        "amount",
        "balance_after",
        "description",
        "created_at"
    )

    search_fields = ("wallet__user__email",)

    list_filter = ("entry_type",)