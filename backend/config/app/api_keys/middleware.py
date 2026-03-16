from django.http import JsonResponse
from .models import APIKey


class APIKeyMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        key = request.headers.get("X-API-KEY")

        if not key:
            return self.get_response(request)

        valid = APIKey.objects.filter(
            key=key,
            active=True
        ).exists()

        if not valid:

            return JsonResponse(
                {"error": "Invalid API key"},
                status=401
            )

        return self.get_response(request)