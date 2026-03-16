from django.core.management.base import BaseCommand
from django.utils import timezone
from bookings.models import Reservation


class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        Reservation.objects.filter(
            status="pending",
            expires_at__lt=timezone.now()
        ).update(status="expired")