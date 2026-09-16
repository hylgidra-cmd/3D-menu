from decimal import Decimal

from django.db import transaction
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.eat.models import Eat
from apps.restaurant.models import RestaurantStaff
from apps.restaurant.permissions import is_restaurant_role
from apps.table.models import Table
from .models import Order, OrderItem
from .serializers import OrderSerializer


class PublicOrderCreateAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get("table_token")
        items = request.data.get("items")
        payment_method = request.data.get("payment_method")
        note = str(request.data.get("note") or "")[:500]
        table = Table.objects.select_related("restaurant").filter(token=token, is_active=True, restaurant__is_active=True).first()
        if not table:
            return Response({"detail": "Stol yoki QR kod faol emas."}, status=404)
        if payment_method not in Order.PaymentMethod.values:
            return Response({"payment_method": ["To'lov usulini tanlang."]}, status=400)
        if not isinstance(items, list) or not items:
            return Response({"items": ["Savat bo'sh."]}, status=400)

        quantities = {}
        for item in items:
            try:
                eat_id, quantity = int(item.get("eat")), int(item.get("quantity"))
            except (AttributeError, TypeError, ValueError):
                return Response({"items": ["Taom ma'lumoti noto'g'ri."]}, status=400)
            if quantity < 1 or quantity > 99:
                return Response({"items": ["Taom soni 1 dan 99 gacha bo'lishi kerak."]}, status=400)
            quantities[eat_id] = quantities.get(eat_id, 0) + quantity

        eats = {eat.id: eat for eat in Eat.objects.filter(id__in=quantities, restaurant=table.restaurant)}
        if len(eats) != len(quantities):
            return Response({"items": ["Tanlangan taom menyuda topilmadi."]}, status=400)

        with transaction.atomic():
            order = Order.objects.create(restaurant=table.restaurant, table=table, payment_method=payment_method, note=note)
            total = Decimal("0")
            for eat_id, quantity in quantities.items():
                eat = eats[eat_id]
                OrderItem.objects.create(order=order, eat=eat, name=eat.name, price=eat.price, quantity=quantity)
                total += eat.price * quantity
            order.total = total
            order.save(update_fields=["total"])
        return Response(OrderSerializer(order).data, status=201)


class OrderListAPIView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        restaurant_id = self.request.query_params.get("restaurant")
        if not restaurant_id:
            return Order.objects.none()
        if not is_restaurant_role(self.request.user, restaurant_id, RestaurantStaff.Role.OWNER, RestaurantStaff.Role.MANAGER):
            return Order.objects.none()
        return Order.objects.filter(restaurant_id=restaurant_id).select_related("table").prefetch_related("items")


class OrderDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Order.objects.select_related("table").prefetch_related("items")

    def patch(self, request, *args, **kwargs):
        order = self.get_object()
        if not is_restaurant_role(request.user, order.restaurant, RestaurantStaff.Role.OWNER, RestaurantStaff.Role.MANAGER):
            return Response({"detail": "Ruxsat yo'q."}, status=403)
        status_value = request.data.get("status")
        if status_value not in Order.Status.values:
            return Response({"status": ["Buyurtma holati noto'g'ri."]}, status=400)
        order.status = status_value
        order.save(update_fields=["status", "updated_at"])
        return Response(OrderSerializer(order).data)
