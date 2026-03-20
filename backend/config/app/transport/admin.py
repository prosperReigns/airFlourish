from django.contrib import admin
from .models import Trip, Vehicle, TripAssignment, TransportBooking


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "organization",
        "pickup_location",
        "dropoff_location",
        "departure_time",
        "arrival_time",
        "flight_number",
        "airline",
        "expected_arrival_time",
        "capacity",
        "booked_seats",
        "is_shared",
        "price_per_seat",
        "currency",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "is_shared", "departure_time")
    search_fields = ("name", "pickup_location", "dropoff_location", "organization")
    ordering = ("-departure_time",)
    readonly_fields = ("booked_seats", "created_at")

    fieldsets = (
        ("Basic Info", {
            "fields": ("name", "organization")
        }),
        ("Route", {
            "fields": ("pickup_location", "dropoff_location")
        }),
        ("Timing", {
            "fields": ("departure_time", "arrival_time")
        }),
        ("Flight Info", {
            "fields": ("flight_number", "airline", "expected_arrival_time")
        }),
        ("Capacity & Pricing", {
            "fields": ("capacity", "booked_seats", "price_per_seat", "currency", "is_shared")
        }),
        ("Status", {
            "fields": ("status",)
        }),
    )


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("plate_number", "vehicle_type", "capacity", "provider", "status", "is_active")
    list_filter = ("vehicle_type", "status", "is_active")
    search_fields = ("plate_number", "provider")
    ordering = ("plate_number",)


@admin.register(TripAssignment)
class TripAssignmentAdmin(admin.ModelAdmin):
    list_display = ("id", "trip", "vehicle", "driver", "status", "assigned_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("trip__name", "vehicle__plate_number", "driver__email")
    autocomplete_fields = ("trip", "vehicle", "driver")
    ordering = ("-assigned_at",)


@admin.register(TransportBooking)
class TransportBookingAdmin(admin.ModelAdmin):
    list_display = ("id", "trip", "user", "passengers", "status", "organisation", "reference", "created_at", "expires_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__email", "trip__name", "organization")
    autocomplete_fields = ("trip", "user")
    ordering = ("-created_at",)