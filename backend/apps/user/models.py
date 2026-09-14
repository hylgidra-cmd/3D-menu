from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = "superadmin", "Super Admin"
        OWNER = "owner", "Restaurant Owner"
        STAFF = "staff", "Restaurant Staff"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OWNER, verbose_name="Role")

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.SUPERADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
