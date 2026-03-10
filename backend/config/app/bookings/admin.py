from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
            "reference_code",
            "user",
            "service_type",
            "status",
            "total_price",
            "created_at",
            )
    list_filter = ("service_type", "status", "created_at")
    search_fields = ("reference_code", "user__username")
