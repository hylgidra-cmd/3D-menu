from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.restaurant.models import RestaurantStaff
from apps.restaurant.permissions import is_restaurant_role
from apps.restaurant.serializers import PublicRestaurantSerializer
from apps.eat.serializers import PublicCategorySerializer
from .models import Table
from .serializers import TableSerializer
from .permissions import IsMineTable


class TableListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = TableSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [IsMineTable()]

    def get_queryset(self):
        queryset = Table.objects.all()
        restaurant_id = self.request.query_params.get("restaurant")
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        restaurant = serializer.validated_data["restaurant"]
        if not is_restaurant_role(request.user, restaurant, RestaurantStaff.Role.OWNER, RestaurantStaff.Role.MANAGER):
            return Response({"detail": "You do not have permission to perform this action."}, status=403)

        serializer.save()
        return Response(TableSerializer(serializer.instance).data, status=201)


class TableDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Table.objects.all()
    serializer_class = TableSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [IsMineTable()]


class PublicTableMenuAPIView(APIView):
    """
    Token-scoped, unauthenticated menu lookup for the QR flow.
    Only the table's own token is accepted - no restaurant/table id is ever
    read from the client, so a QR code can only ever resolve to the one
    restaurant it was generated for.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        table = (
            Table.objects.select_related("restaurant")
            .filter(token=token, is_active=True, restaurant__is_active=True)
            .first()
        )
        if not table:
            return Response({"detail": "Menu not found"}, status=status.HTTP_404_NOT_FOUND)

        restaurant = table.restaurant
        categories = restaurant.categories.filter(is_active=True).prefetch_related("eats")

        return Response({
            "table": {"id": table.id, "name": table.name, "place": table.place},
            "restaurant": PublicRestaurantSerializer(restaurant).data,
            "categories": PublicCategorySerializer(categories, many=True).data,
        })
