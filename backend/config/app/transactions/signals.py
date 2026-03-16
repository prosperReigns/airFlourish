from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transaction
from app.notifications.models import Notification

@receiver(post_save, sender=Transaction)
def create_transaction_notification(sender, instance, created, **kwargs):
    if created:
        # Determine notification type
        notification_type = (
            "success"
            if instance.status == "successful"
            else "error"
            if instance.status == "failed"
            else "info"
        )

        title_map = {
            "pending": "Transaction Pending",
            "successful": "Transaction Successful",
            "failed": "Transaction Failed",
        }

        Notification.objects.create(
            user=instance.user,
            title=title_map.get(instance.status, "Transaction Update"),
            message=f"Transaction {instance.reference} of {instance.amount} {instance.currency} is {instance.status}.",
            notification_type=notification_type
        )
