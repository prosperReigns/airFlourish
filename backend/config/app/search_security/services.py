from datetime import timedelta
from django.utils import timezone
from .models import SearchLog


MAX_SEARCH_PER_MINUTE = 30


def search_allowed(user, ip):

    window = timezone.now() - timedelta(minutes=1)

    count = SearchLog.objects.filter(
        ip_address=ip,
        created_at__gte=window
    ).count()

    return count < MAX_SEARCH_PER_MINUTE

def record_search(user, ip, endpoint):

    SearchLog.objects.create(
        user=user,
        ip_address=ip,
        endpoint=endpoint
    )