from django.contrib import admin
from .models import HotelReservation

@admin.register(HotelReservation)
class HotelReservationAdmin(admin.ModelAdmin):
    list_display = (
            "booking",
            "hotel_name",
            "check_in",
            "check_out",
            "guests",
            )
