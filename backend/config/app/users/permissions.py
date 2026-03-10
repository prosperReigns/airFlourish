from rest_framework.permissions import BasePermission


class IsAgent(BasePermission):
    """Custom permission to only allow users with user_type 'agent' to access certain views.
    This permission checks the user_type attribute of the user and grants access only if it is set to 'agent'.
    Expected usage: Add this permission to views that should only be accessible by agent users.
    """
    def has_permission(self, request, view):
        """Checks if the user is authenticated and has a user_type of 'agent'."""
        return request.user.is_authenticated and request.user.user_type == "agent"


class IsAdminUserType(BasePermission):
    """Custom permission to only allow users with user_type 'admin' to access certain views.
    This permission checks the user_type attribute of the user and grants access only if it is set to 'admin'.
    Expected usage: Add this permission to views that should only be accessible by admin users.
    """
    def has_permission(self, request, view):
        """Checks if the user is authenticated and has a user_type of 'admin'."""
        return request.user.is_authenticated and request.user.user_type == "admin"


class IsCorporateUser(BasePermission):
    """Custom permission to only allow users with user_type 'corporate' to access certain views.
    This permission checks the user_type attribute of the user and grants access only if it is set to 'corporate'.
    Expected usage: Add this permission to views that should only be accessible by corporate users.
    """
    def has_permission(self, request, view):
        """Checks if the user is authenticated and has a user_type of 'corporate'."""
        return request.user.is_authenticated and request.user.user_type == "corporate"
