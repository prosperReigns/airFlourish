from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from .models import BookingLock


def acquire_lock(resource_type, resource_id, user):

    expiration = timezone.now() + timedelta(minutes=5)

    try:

        with transaction.atomic():

            lock = BookingLock.objects.create(
                resource_type=resource_type,
                resource_id=resource_id,
                user=user,
                expires_at=expiration
            )

            return lock

    except Exception:

        existing = BookingLock.objects.filter(
            resource_type=resource_type,
            resource_id=resource_id
        ).first()

        if existing and existing.expires_at > timezone.now():
            raise Exception("Resource currently locked")

        existing.delete()

        return acquire_lock(resource_type, resource_id, user)