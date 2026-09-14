from django.contrib.auth import get_user_model
from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.utils.text import slugify

User = get_user_model()

class Restaurant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="restaurant_user")
    name = models.CharField(max_length=200, validators=[MinLengthValidator(3), MaxLengthValidator(255)], verbose_name="Name")
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name="Slug")
    description = models.TextField(validators=[MinLengthValidator(3), MaxLengthValidator(500)], blank=True, null=True, verbose_name="Description")
    location = models.CharField(max_length=200, blank=True, null=True, verbose_name="Location")
    coordinates = models.JSONField(default=dict, blank=True, null=True, verbose_name="Coordinates")
    logo = models.ImageField(upload_to="restaurant/logos/", blank=True, null=True, verbose_name="Logo")
    cover_image = models.ImageField(upload_to="restaurant/covers/", blank=True, null=True, verbose_name="Cover image")
    primary_color = models.CharField(max_length=7, default="#111827", verbose_name="Primary color")
    is_active = models.BooleanField(default=True, verbose_name="Is active")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "restaurant"
            slug = base_slug
            i = 1
            while Restaurant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base_slug}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Restaurant {self.name}"

    class Meta:
        verbose_name = "Restaurant"
        verbose_name_plural = "Restaurants"
        ordering = ["-created_at"]


class RestaurantStaff(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MANAGER = "manager", "Manager"
        WAITER = "waiter", "Waiter"

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="staff")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="restaurant_roles")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.WAITER, verbose_name="Role")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")

    def __str__(self):
        return f"{self.user} - {self.restaurant} ({self.role})"

    class Meta:
        verbose_name = "Restaurant staff"
        verbose_name_plural = "Restaurant staff"
        unique_together = ("restaurant", "user")
