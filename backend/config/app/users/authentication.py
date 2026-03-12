from django.core.cache import cache
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


BLACKLIST_PREFIX = "blacklisted_access_jti:"


class CustomJWTAuthentication(JWTAuthentication):
    """JWT auth that normalizes invalid token errors and supports access blacklist."""

    def get_validated_token(self, raw_token):
        try:
            validated = super().get_validated_token(raw_token)
        except Exception:
            raise AuthenticationFailed("Invalid token")

        jti = validated.get("jti")
        if jti and cache.get(f"{BLACKLIST_PREFIX}{jti}"):
            raise AuthenticationFailed("Invalid token")

        return validated
