from rest_framework import permissions

class IsMe(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and request.user == obj or request.user.is_superuser

class IsMine(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and request.user == obj.user or request.user.is_superuser


class IsSuperUser(permissions.BasePermission):
    """Platform-admin-only actions (restaurant activation, global stats)."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)