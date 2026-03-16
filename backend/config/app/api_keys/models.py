import uuid
import secrets
from django.db import models


class APIKey(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    name = models.CharField(max_length=255)

    key = models.CharField(max_length=64, unique=True)

    active = models.BooleanField(default=True)

    rate_limit = models.IntegerField(default=1000)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        if not self.key:
            self.key = secrets.token_hex(32)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name