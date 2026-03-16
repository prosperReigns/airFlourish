from django.db import models


class BlockedIP(models.Model):

    ip_address = models.GenericIPAddressField(unique=True)

    reason = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)

class PaymentAttempt(models.Model):

    user = models.ForeignKey("users.User", on_delete=models.CASCADE)

    success = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)