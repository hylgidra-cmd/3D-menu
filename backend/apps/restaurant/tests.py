import io

from django.contrib.auth import get_user_model
from PIL import Image
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Restaurant, RestaurantStaff

User = get_user_model()


def make_image_file(name="test.png"):
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=(200, 50, 50)).save(buf, format="PNG")
    buf.seek(0)
    buf.name = name
    return buf


class RestaurantCreationTests(APITestCase):
    """Regression tests for two real bugs found during development:
    restaurant creation was blocked for ordinary users (IsAdminUser instead
    of IsAuthenticated), and multipart uploads (logo/cover) were rejected."""

    def setUp(self):
        self.user = User.objects.create_user(username="new_owner", password="Passw0rd123")
        self.client.force_authenticate(user=self.user)

    def test_authenticated_user_can_create_restaurant(self):
        res = self.client.post("/api/restaurant/", {"name": "My Diner"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            RestaurantStaff.objects.filter(
                restaurant_id=res.data["id"], user=self.user, role=RestaurantStaff.Role.OWNER
            ).exists()
        )

    def test_restaurant_creation_accepts_multipart_with_logo(self):
        res = self.client.post(
            "/api/restaurant/",
            {"name": "Diner With Logo", "logo": make_image_file()},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)


class RestaurantRolePermissionTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="x")
        self.manager = User.objects.create_user(username="manager", password="x")
        self.waiter = User.objects.create_user(username="waiter", password="x")
        self.restaurant = Restaurant.objects.create(user=self.owner, name="Test Place")
        RestaurantStaff.objects.create(restaurant=self.restaurant, user=self.owner, role=RestaurantStaff.Role.OWNER)
        RestaurantStaff.objects.create(restaurant=self.restaurant, user=self.manager, role=RestaurantStaff.Role.MANAGER)
        RestaurantStaff.objects.create(restaurant=self.restaurant, user=self.waiter, role=RestaurantStaff.Role.WAITER)

    def test_waiter_cannot_create_category(self):
        self.client.force_authenticate(user=self.waiter)
        res = self.client.post("/api/eat/category/", {"restaurant": self.restaurant.id, "name": "Drinks"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_create_category(self):
        self.client.force_authenticate(user=self.manager)
        res = self.client.post("/api/eat/category/", {"restaurant": self.restaurant.id, "name": "Drinks"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
