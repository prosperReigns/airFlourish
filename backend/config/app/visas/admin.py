from django.contrib import admin
from .models import VisaApplication

@admin.register(VisaApplication)
class VisaApplicationAdmin(admin.ModelAdmin):
    list_display = (
            "booking",
            "destination_country",
            "visa_type",
            "appointment_date",
            "document_status",
            )
    list_filter = ("document_status",)
