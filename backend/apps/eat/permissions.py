from apps.restaurant.permissions import restaurant_role_permission
from apps.restaurant.models import RestaurantStaff

# Owner + manager can create/edit menu items and categories; waiters are read-only here.
IsMineEat = restaurant_role_permission(
    RestaurantStaff.Role.OWNER, RestaurantStaff.Role.MANAGER
)
