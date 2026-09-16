from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "eat", "name", "price", "quantity"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    table_name = serializers.CharField(source="table.name", read_only=True)

    class Meta:
        model = Order
        fields = ["id", "restaurant", "table", "table_name", "status", "payment_method", "note", "total", "created_at", "items"]
        read_only_fields = ["restaurant", "table", "total", "created_at"]
