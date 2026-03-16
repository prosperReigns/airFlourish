import uuid
from django.db import models


class Event(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    event_type = models.CharField(max_length=100)

    payload = models.JSONField()

    processed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    processed_at = models.DateTimeField(null=True, blank=True)