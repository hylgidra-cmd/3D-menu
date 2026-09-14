from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.user.permissions import IsMine, IsSuperUser
from apps.table.models import Table
from apps.eat.models import Eat
from .models import Restaurant, RestaurantStaff
from .permissions import is_restaurant_role
from .serializers import (
    RestaurantSerializer,
    MyRestaurantSerializer,
    RestaurantStaffSerializer,
    InviteStaffSerializer,
)

User = get_user_model()


class RestaurantListCreateAPIView(generics.ListCreateAPIView):
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.request.user)
        RestaurantStaff.objects.get_or_create(
            restaurant=serializer.instance,
            user=self.request.user,
            defaults={"role": RestaurantStaff.Role.OWNER},
        )
        return Response(RestaurantSerializer(serializer.instance).data, status=201)

class RestaurantDetailAPIView(generics.RetrieveUpdateAPIView):
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [IsMine()]


class MyRestaurantsAPIView(generics.ListAPIView):
    """Restaurants the current user has a staff role on - powers the admin panel's restaurant switcher."""
    serializer_class = MyRestaurantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Restaurant.objects.filter(staff__user=self.request.user).distinct()

    def get_serializer_context(self):
        return {"request": self.request}


class RestaurantStaffListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = RestaurantStaffSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_restaurant(self):
        return generics.get_object_or_404(Restaurant, pk=self.kwargs["pk"])

    def get_queryset(self):
        return RestaurantStaff.objects.filter(restaurant_id=self.kwargs["pk"]).select_related("user")

    def list(self, request, *args, **kwargs):
        restaurant = self.get_restaurant()
        if not is_restaurant_role(request.user, restaurant, RestaurantStaff.Role.OWNER, RestaurantStaff.Role.MANAGER):
            return Response({"detail": "You do not have permission to perform this action."}, status=403)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        restaurant = self.get_restaurant()
        if not is_restaurant_role(request.user, restaurant, RestaurantStaff.Role.OWNER):
            return Response({"detail": "Faqat restoran egasi xodim qo'sha oladi."}, status=403)

        serializer = InviteStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff, created = RestaurantStaff.objects.update_or_create(
            restaurant=restaurant,
            user=serializer._user,
            defaults={"role": serializer.validated_data["role"]},
        )
        return Response(RestaurantStaffSerializer(staff).data, status=201 if created else 200)


class RestaurantStaffDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, staff_id):
        restaurant = generics.get_object_or_404(Restaurant, pk=pk)
        if not is_restaurant_role(request.user, restaurant, RestaurantStaff.Role.OWNER):
            return Response({"detail": "Faqat restoran egasi xodimni o'chira oladi."}, status=403)

        staff = generics.get_object_or_404(RestaurantStaff, pk=staff_id, restaurant=restaurant)
        if staff.role == RestaurantStaff.Role.OWNER:
            remaining_owners = RestaurantStaff.objects.filter(
                restaurant=restaurant, role=RestaurantStaff.Role.OWNER
            ).exclude(pk=staff.pk).count()
            if remaining_owners == 0:
                return Response({"detail": "Restoranda kamida bitta owner qolishi kerak."}, status=400)

        staff.delete()
        return Response(status=204)


class RestaurantActivationAPIView(APIView):
    """Platform-admin-only: suspend/reactivate a restaurant (owners cannot self-reactivate)."""
    permission_classes = [IsSuperUser]

    def patch(self, request, pk):
        restaurant = generics.get_object_or_404(Restaurant, pk=pk)
        is_active = request.data.get("is_active")
        if not isinstance(is_active, bool):
            return Response({"detail": "'is_active' bool bo'lishi kerak."}, status=400)

        restaurant.is_active = is_active
        restaurant.save(update_fields=["is_active"])
        return Response(RestaurantSerializer(restaurant).data)


class PlatformStatsAPIView(APIView):
    """Platform-admin-only: global counts for the super-admin dashboard."""
    permission_classes = [IsSuperUser]

    def get(self, request):
        return Response({
            "restaurants": {
                "total": Restaurant.objects.count(),
                "active": Restaurant.objects.filter(is_active=True).count(),
                "inactive": Restaurant.objects.filter(is_active=False).count(),
            },
            "users": User.objects.count(),
            "tables": Table.objects.count(),
            "eats": {
                "total": Eat.objects.count(),
                "with_3d_model": sum(1 for e in Eat.objects.only("model_json") if e.model_url),
            },
        })
