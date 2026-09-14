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

    def test_manager_cannot_invite_staff(self):
        outsider = User.objects.create_user(username="outsider", password="x")
        self.client.force_authenticate(user=self.manager)
        res = self.client.post(
            f"/api/restaurant/{self.restaurant.id}/staff/",
            {"username": outsider.username, "role": "waiter"},
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_invite_staff(self):
        outsider = User.objects.create_user(username="outsider2", password="x")
        self.client.force_authenticate(user=self.owner)
        res = self.client.post(
            f"/api/restaurant/{self.restaurant.id}/staff/",
            {"username": outsider.username, "role": "waiter"},
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_cannot_invite_someone_as_owner_via_invite_endpoint(self):
        outsider = User.objects.create_user(username="outsider3", password="x")
        self.client.force_authenticate(user=self.owner)
        res = self.client.post(
            f"/api/restaurant/{self.restaurant.id}/staff/",
            {"username": outsider.username, "role": "owner"},
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_last_owner_cannot_be_removed(self):
        owner_staff = RestaurantStaff.objects.get(restaurant=self.restaurant, user=self.owner)
        self.client.force_authenticate(user=self.owner)
        res = self.client.delete(f"/api/restaurant/{self.restaurant.id}/staff/{owner_staff.id}/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(RestaurantStaff.objects.filter(pk=owner_staff.pk).exists())
