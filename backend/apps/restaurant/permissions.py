from rest_framework import permissions
from .models import Restaurant, RestaurantStaff


class IsOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or RestaurantStaff.objects.filter(user=request.user).exists()
        )


def restaurant_role_permission(*roles):
    """
    Returns a DRF permission class granting access only to authenticated users
    who hold one of `roles` on the specific Restaurant tied to the object
    (or, for has_permission-only checks, any restaurant at all).
    Superusers always pass.
    """

    class _RestaurantRolePermission(permissions.BasePermission):
        def has_permission(self, request, view):
            if not request.user.is_authenticated:
                return False
            if request.user.is_superuser:
                return True
            return RestaurantStaff.objects.filter(user=request.user, role__in=roles).exists()

        def has_object_permission(self, request, view, obj):
            if not request.user.is_authenticated:
                return False
            if request.user.is_superuser:
                return True
            restaurant = obj if isinstance(obj, Restaurant) else getattr(obj, "restaurant", None)
            if restaurant is None:
                return False
            return RestaurantStaff.objects.filter(restaurant=restaurant, user=request.user, role__in=roles).exists()

    return _RestaurantRolePermission


def is_restaurant_role(user, restaurant, *roles):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return RestaurantStaff.objects.filter(restaurant=restaurant, user=user, role__in=roles).exists()
