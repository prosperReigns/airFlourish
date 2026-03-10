from rest_framework import permissions

class IsAdminUserType(permissions.BasePermission):
    """Custom permission to allow access only to admin users based on the user_type attribute of the user model. This permission checks if the authenticated user's user_type is set to "admin". If the user is an admin, they are granted access; otherwise, access is denied. This permission can be used in viewsets or API views to restrict certain actions or endpoints to admin users only."""
    def has_permission(self, request, view):
        return getattr(request.user, "user_type", None) == "admin"