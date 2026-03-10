from django.contrib import admin
from .models import TransportService

@admin.register(TransportService)
class TransportServiceAdmin(admin.ModelAdmin):
    list_display = (
            "booking",
            "pickup_location",
            "dropoff_location",
            "vehicle_type",
            )
