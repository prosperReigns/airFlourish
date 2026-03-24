from django.contrib import admin
from .models import Airport, FlightBooking

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


@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ("code", "city", "name", "country")
    search_fields = ("code", "city", "name", "country")
