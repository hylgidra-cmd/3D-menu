from apps.restaurant.permissions import restaurant_role_permission
from apps.restaurant.models import RestaurantStaff

# Owner + manager manage tables/QR codes; waiters are read-only here.
IsMineTable = restaurant_role_permission(
    RestaurantStaff.Role.OWNER, RestaurantStaff.Role.MANAGER
)
