from rest_framework import permissions

class IsAdminUserType(permissions.BasePermission):
    """Custom permission to only allow users with user_type 'admin' to access certain views.
    This permission checks the user_type attribute of the user and grants access only if it is set to 'admin'.
    Expected usage: Add this permission to views that should only be accessible by admin users.
    """
    def has_permission(self, request, view):
        return getattr(request.user, "user_type", None) == "admin"