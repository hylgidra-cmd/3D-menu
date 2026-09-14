import uuid
from io import BytesIO

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models

from apps.restaurant.models import Restaurant


class Table(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='table_restaurant')
    name = models.CharField(max_length=100)
    place = models.CharField(max_length=100)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    qr_code = models.ImageField(upload_to="qrcodes/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.restaurant} - Table {self.name}"

    def menu_url(self):
        return f"{settings.FRONTEND_BASE_URL}/menu/{self.token}"

    def generate_qr_code(self):
        img = qrcode.make(self.menu_url())
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        filename = f"table-{self.token}.png"
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=["qr_code"])
