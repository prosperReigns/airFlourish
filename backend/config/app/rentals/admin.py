from django.contrib import admin
from .models import CarRental


@admin.register(CarRental)
class CarRentalAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "vehicle",
        "user",
        "start_date",
        "end_date",
        "daily_rate",
        "total_price",
        "pickup_location",
        "dropoff_location",
        "deposit_amount",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "start_date", "vehicle")
    search_fields = ("user__email", "vehicle__plate_number")
    autocomplete_fields = ("vehicle", "user")
    ordering = ("-created_at",)

    fieldsets = (
        ("Rental Info", {
            "fields": ("vehicle", "user", "status")
        }),
        ("Schedule", {
            "fields": ("start_date", "end_date")
        }),
        ("Locations", {
            "fields": ("pickup_location", "dropoff_location")
        }),
        ("Pricing", {
            "fields": ("daily_rate", "total_price", "deposit_amount")
        }),
    )