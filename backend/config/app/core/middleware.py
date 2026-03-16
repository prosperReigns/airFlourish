import hashlib
import json
from django.http import JsonResponse



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

            return JsonResponse(
                record.response_body,
                status=record.status_code
            )

        response = self.get_response(request)

        IdempotencyKey.objects.create(
            key=key,
            request_hash=request_hash,
            response_body=getattr(response, "data", {}),
            status_code=response.status_code
        )

        return response