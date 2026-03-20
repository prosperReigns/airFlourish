from django.contrib import admin
from .models import Inventory


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "provider",
        "resource_type",
        "resource_id",
        "start_time",
        "end_time",
        "pickup_location",
        "dropoff_location",
        "available_quantity",
        "price",
        "currency",
        "last_synced",
        "updated_at",
    )
    list_filter = ("resource_type", "provider", "start_time")
    search_fields = ("resource_id", "pickup_location", "dropoff_location")
    ordering = ("-last_synced",)

    fieldsets = (
        ("Resource Info", {
            "fields": ("provider", "resource_type", "resource_id")
        }),
        ("Timing", {
            "fields": ("start_time", "end_time")
        }),
        ("Route", {
            "fields": ("pickup_location", "dropoff_location")
        }),
        ("Availability", {
            "fields": ("available_quantity",)
        }),
        ("Pricing", {
            "fields": ("price", "currency")
        }),
        ("Metadata", {
            "fields": ("metadata",)
        }),
    )