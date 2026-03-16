from django.contrib import admin
from .models import APIKey


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "key",
        "active",
        "rate_limit",
        "created_at",
    )

    search_fields = ("name", "key")