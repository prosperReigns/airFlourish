from django.db import models
from django.conf import settings


class SearchLog(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    ip_address = models.GenericIPAddressField()

    endpoint = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)