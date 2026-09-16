import io
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from apps.restaurant.models import Restaurant, RestaurantStaff
from .models import Category, Eat

User = get_user_model()


def valid_image_upload(name):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color=(200, 50, 50)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class EatModelProviderErrorTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="Passw0rd123")
        self.restaurant = Restaurant.objects.create(user=self.user, name="Test Cafe")
        RestaurantStaff.objects.create(
            restaurant=self.restaurant,
            user=self.user,
            role=RestaurantStaff.Role.OWNER,
        )
        self.eat = Eat.objects.create(
            restaurant=self.restaurant,
            name="Palov",
            description="Uzbek rice with meat",
            price="25000.00",
            image=SimpleUploadedFile("palov.jpg", b"image", content_type="image/jpeg"),
            task_json={"task_id": "old-task-id"},
        )

    def test_check_model_requires_django_authentication(self):
        response = self.client.get(f"/api/eat/check-model/{self.eat.id}/", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"].code, "not_authenticated")

    def test_provider_task_error_is_saved_on_eat_card_state(self):
        self.client.force_authenticate(self.user)
        provider_error = {
            "error_type": "TASK_NOT_FOUND",
            "error_code": "TASK_NOT_FOUND",
            "error": "3D task topilmadi. Modelni qayta generatsiya qilish kerak.",
            "provider_http_status": 404,
            "provider_json": {"detail": "No PublicAPIGenerationRequest matches the given query."},
        }

        with patch("apps.eat.views.api.show_model", return_value=provider_error):
            response = self.client.get(f"/api/eat/check-model/{self.eat.id}/", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.eat.refresh_from_db()
        self.assertEqual(self.eat.model_json["error_type"], "TASK_NOT_FOUND")
        self.assertEqual(response.data["model_error_type"], "TASK_NOT_FOUND")

    def test_failed_regeneration_without_model_file_keeps_old_task_and_shows_new_error(self):
        self.client.force_authenticate(self.user)
        old_task_json = dict(self.eat.task_json)
        provider_error = {
            "error_type": "INSUFFICIENT_CREDITS",
            "error_code": "INSUFFICIENT_CREDITS",
            "error": "3D API krediti tugagan.",
            "provider_http_status": 402,
        }

        with patch("apps.eat.views.api.send_image", return_value=provider_error):
            response = self.client.post(f"/api/eat/regenerate-model/{self.eat.id}/", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.eat.refresh_from_db()
        self.assertEqual(self.eat.task_json, old_task_json)
        self.assertEqual(self.eat.model_json["error_type"], "INSUFFICIENT_CREDITS")
        self.assertFalse(self.eat.model_file)

    def test_failed_regeneration_never_destroys_working_model_file(self):
        self.eat.model_file.save("existing.glb", ContentFile(b"glb"), save=True)
        old_task_json = dict(self.eat.task_json)
        old_model_name = self.eat.model_file.name
        self.client.force_authenticate(self.user)
        provider_error = {
            "error_type": "INSUFFICIENT_CREDITS",
            "error_code": "INSUFFICIENT_CREDITS",
            "error": "3D API krediti tugagan.",
            "provider_http_status": 402,
        }

        with patch("apps.eat.views.api.send_image", return_value=provider_error):
            response = self.client.post(f"/api/eat/regenerate-model/{self.eat.id}/", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.eat.refresh_from_db()
        self.assertEqual(self.eat.task_json, old_task_json)
        self.assertEqual(self.eat.model_file.name, old_model_name)

    def test_regenerate_usdz_reuses_the_existing_model_without_calling_provider(self):
        self.eat.model_file.save("existing.glb", ContentFile(b"glb"), save=True)
        self.client.force_authenticate(self.user)

        with patch("apps.eat.views.normalize_glb_bytes", return_value=(b"normalized-glb", {"changed": False})), \
             patch("apps.eat.views.convert_glb_to_usdz", return_value=b"usdz") as convert:
            response = self.client.post(f"/api/eat/regenerate-usdz/{self.eat.id}/", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.eat.refresh_from_db()
        convert.assert_called_once_with(b"normalized-glb")
        self.assertTrue(self.eat.model_file_usdz.name.endswith(".usdz"))
        self.assertEqual(self.eat.usdz_json, {})


class CategoryApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="category_owner", password="Passw0rd123")
        self.restaurant = Restaurant.objects.create(user=self.user, name="Category Cafe")
        RestaurantStaff.objects.create(
            restaurant=self.restaurant,
            user=self.user,
            role=RestaurantStaff.Role.OWNER,
        )
        self.hidden_category = Category.objects.create(
            restaurant=self.restaurant,
            name="Mavsumiy",
            icon="🍰",
            is_active=False,
        )

    def test_category_list_includes_icon_and_eat_count(self):
        Eat.objects.create(
            restaurant=self.restaurant,
            category=self.hidden_category,
            name="Mavsumiy desert",
            description="Yashirilgan kategoriya bilan oldingi taom",
            price="15000.00",
            image=SimpleUploadedFile("dessert.jpg", b"image", content_type="image/jpeg"),
        )

        response = self.client.get(f"/api/eat/category/?restaurant={self.restaurant.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category = response.data["results"][0]
        self.assertEqual(category["icon"], "🍰")
        self.assertEqual(category["eats_count"], 1)

    def test_hidden_category_cannot_be_selected_for_a_new_eat(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            "/api/eat/",
            {
                "restaurant": self.restaurant.id,
                "category": self.hidden_category.id,
                "name": "Yangi desert",
                "description": "Yashirilgan kategoriya tekshiruvi",
                "price": "18000.00",
                "image": valid_image_upload("new-dessert.png"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", response.data)

    def test_existing_eat_keeps_its_hidden_category_when_edited(self):
        eat = Eat.objects.create(
            restaurant=self.restaurant,
            category=self.hidden_category,
            name="Eski desert",
            description="Avvaldan biriktirilgan yashirilgan kategoriya",
            price="16000.00",
            image=SimpleUploadedFile("old-dessert.jpg", b"image", content_type="image/jpeg"),
        )
        self.client.force_authenticate(self.user)

        response = self.client.patch(f"/api/eat/{eat.id}/", {"name": "Yangilangan desert"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        eat.refresh_from_db()
        self.assertEqual(eat.category_id, self.hidden_category.id)
