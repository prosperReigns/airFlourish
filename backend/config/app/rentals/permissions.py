from rest_framework import permissions


class IsAdminUserType(permissions.BasePermission):
    """Allow access only to admin users based on the user_type attribute."""

    def has_permission(self, request, view):
        return getattr(request.user, "user_type", None) == "admin"


class IsAdminOrReadOnlyUserType(permissions.BasePermission):
    """Allow read-only access for authenticated users, write access for admins."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return getattr(request.user, "user_type", None) == "admin"
