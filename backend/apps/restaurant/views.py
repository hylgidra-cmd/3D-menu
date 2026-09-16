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
