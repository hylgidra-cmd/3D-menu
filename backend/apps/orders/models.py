from django.db import models

from apps.eat.models import Eat
from apps.restaurant.models import Restaurant
from apps.table.models import Table


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Yangi"
        ACCEPTED = "accepted", "Qabul qilindi"
        PREPARING = "preparing", "Tayyorlanmoqda"
        READY = "ready", "Tayyor"
        SERVED = "served", "Yetkazildi"
        CANCELLED = "cancelled", "Bekor qilindi"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Naqd"
        CARD = "card", "Karta"
        ONLINE = "online", "Onlayn"

    restaurant = models.ForeignKey(Restaurant, on_delete=models.PROTECT, related_name="orders")
    table = models.ForeignKey(Table, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    payment_method = models.CharField(max_length=16, choices=PaymentMethod.choices)
    note = models.CharField(max_length=500, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    eat = models.ForeignKey(Eat, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items")
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ["id"]
