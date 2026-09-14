from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from apps.restaurant.models import Restaurant, RestaurantStaff
from apps.eat.models import Category, Eat
from .models import Table

User = get_user_model()


def make_restaurant_with_owner(username, restaurant_name):
    user = User.objects.create_user(username=username, password="Passw0rd123")
    restaurant = Restaurant.objects.create(user=user, name=restaurant_name)
    RestaurantStaff.objects.create(restaurant=restaurant, user=user, role=RestaurantStaff.Role.OWNER)
    return user, restaurant


class TableTokenIsolationTests(APITestCase):
    """
    The core product requirement: scanning one restaurant's table QR must
    never surface another restaurant's data.
    """

    def setUp(self):
        self.owner_a, self.restaurant_a = make_restaurant_with_owner("owner_a", "Restaurant A")
        self.owner_b, self.restaurant_b = make_restaurant_with_owner("owner_b", "Restaurant B")

        self.table_a = Table.objects.create(restaurant=self.restaurant_a, name="A1", place="Hall")
        self.table_b = Table.objects.create(restaurant=self.restaurant_b, name="B1", place="Hall")

        category_a = Category.objects.create(restaurant=self.restaurant_a, name="Mains")
        Eat.objects.create(
            restaurant=self.restaurant_a,
            category=category_a,
            name="A-only dish",
            description="Only restaurant A should ever show this",
            price="10.00",
            image="eat/test.png",
        )

    def test_table_token_only_returns_its_own_restaurant(self):
        url = f"/api/public/menu/{self.table_a.token}/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["restaurant"]["name"], "Restaurant A")
        self.assertNotEqual(res.data["restaurant"]["name"], "Restaurant B")

    def test_table_b_token_never_leaks_restaurant_a_data(self):
        url = f"/api/public/menu/{self.table_b.token}/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["restaurant"]["name"], "Restaurant B")
        # Restaurant B has no categories/eats of its own.
        self.assertEqual(res.data["categories"], [])

    def test_unknown_token_returns_404_not_someone_elses_menu(self):
        res = self.client.get("/api/public/menu/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_inactive_restaurant_hides_its_table_menu(self):
        self.restaurant_a.is_active = False
        self.restaurant_a.save(update_fields=["is_active"])
        res = self.client.get(f"/api/public/menu/{self.table_a.token}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_b_cannot_create_a_table_on_restaurant_a(self):
        self.client.force_authenticate(user=self.owner_b)
        res = self.client.post(
            "/api/table/",
            {"restaurant": self.restaurant_a.id, "name": "Hacked", "place": "Hall"},
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Table.objects.filter(name="Hacked").exists())
