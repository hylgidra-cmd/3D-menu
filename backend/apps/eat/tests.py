from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.restaurant.models import Restaurant, RestaurantStaff
from .models import Eat

User = get_user_model()


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
