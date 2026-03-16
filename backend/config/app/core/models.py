import uuid
from django.db import models


class IdempotencyKey(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    key = models.CharField(max_length=255, unique=True)

    request_hash = models.CharField(max_length=255)

    response_body = models.JSONField(null=True, blank=True)

    status_code = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["key"]),
        ]