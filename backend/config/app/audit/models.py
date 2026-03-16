import uuid
from django.db import models
from django.conf import settings


class AuditLog(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    action = models.CharField(max_length=255)

    metadata = models.JSONField(default=dict)

    ip_address = models.GenericIPAddressField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):

        return f"{self.actor} -> {self.action}"