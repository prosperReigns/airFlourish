from django.utils import timezone
from datetime import timedelta
from .models import PaymentAttempt


def is_payment_blocked(user):

    window = timezone.now() - timedelta(minutes=10)

    failures = PaymentAttempt.objects.filter(
        user=user,
        success=False,
        created_at__gte=window
    ).count()

    return failures >= 3