from django.core.cache import cache
from django.conf import settings
import time


CIRCUIT_FAILURE_LIMIT = 5
CIRCUIT_TIMEOUT = 120  # seconds (2 minutes)


def is_circuit_open(service_name="booking_api"):
    key = f"circuit_open_{service_name}"
    return cache.get(key)


def record_failure(service_name="booking_api"):
    failure_key = f"circuit_failures_{service_name}"
    open_key = f"circuit_open_{service_name}"

    failures = cache.get(failure_key, 0) + 1
    cache.set(failure_key, failures, timeout=CIRCUIT_TIMEOUT)

    if failures >= CIRCUIT_FAILURE_LIMIT:
        cache.set(open_key, True, timeout=CIRCUIT_TIMEOUT)


def record_success(service_name="booking_api"):
    failure_key = f"circuit_failures_{service_name}"
    open_key = f"circuit_open_{service_name}"

    cache.delete(failure_key)
    cache.delete(open_key)