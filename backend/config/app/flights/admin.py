from django.contrib import admin
from .models import FlightBooking

@admin.register(FlightBooking)
class FlightBookingAdmin(admin.ModelAdmin):
    list_display = (
            "booking",
            "departure_city",
            "arrival_city",
            "departure_date",
            "return_date",
            "passengers",
            )
    search_fields = ("departure_city", "arrival_city")
