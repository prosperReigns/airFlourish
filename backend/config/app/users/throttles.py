from rest_framework.throttling import SimpleRateThrottle

class IPRateThrottle(SimpleRateThrottle):
    scope = "ip"

    def get_cache_key(self, request, view):
        # Get the IP address of the client
        ip = self.get_ident(request)
        if not ip:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": ip
        }