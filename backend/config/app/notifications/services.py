import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notification

logger = logging.getLogger(__name__)


def create_notification(*, user, title: str, message: str, notification_type: str = "info"):
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
    )


def send_email(*, to: str, subject: str, body: str):
    if not to:
        return

    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [to],
            fail_silently=True,
        )
    except Exception:
        logger.exception("Unable to send email to %s", to)
