import hashlib
import json
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone



class IdempotencyMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from .models import IdempotencyKey

        key = request.headers.get("Idempotency-Key")

        if not key:
            return self.get_response(request)

        body = request.body.decode("utf-8")
        request_hash = hashlib.sha256(body.encode()).hexdigest()

        record = IdempotencyKey.objects.filter(key=key).first()

        if record:
            if record.expires_at and record.expires_at <= timezone.now():
                record.delete()
            else:
                if record.request_hash != request_hash:
                    return JsonResponse(
                        {"error": "Idempotency-Key reuse with different payload"},
                        status=409,
                    )
                return JsonResponse(
                    record.response_body,
                    status=record.status_code
                )

        response = self.get_response(request)

        ttl_seconds = getattr(settings, "IDEMPOTENCY_TTL_SECONDS", 24 * 60 * 60)
        expires_at = timezone.now() + timedelta(seconds=ttl_seconds)

        IdempotencyKey.objects.create(
            key=key,
            request_hash=request_hash,
            response_body=getattr(response, "data", {}),
            status_code=response.status_code,
            expires_at=expires_at,
        )

        return response
