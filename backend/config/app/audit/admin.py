from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    list_display = (
        "actor",
        "action",
        "ip_address",
        "created_at"
    )

    search_fields = (
        "actor__email",
        "action",
    )

    list_filter = (
        "created_at",
    )