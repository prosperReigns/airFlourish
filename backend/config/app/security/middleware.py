from django.http import JsonResponse
from .models import BlockedIP


class IPBlockMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        ip = request.META.get("REMOTE_ADDR")

        if BlockedIP.objects.filter(ip_address=ip).exists():

            return JsonResponse(
                {"error": "IP blocked"},
                status=403
            )

        return self.get_response(request)