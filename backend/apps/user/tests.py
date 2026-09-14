from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class RegistrationPrivilegeEscalationTests(APITestCase):
    """Regression test for a critical bug: self-registration used to accept
    `is_superuser`/`is_staff`/`role` straight from the request body, letting
    anyone create a platform-admin account."""

    def test_registration_ignores_is_superuser_and_role(self):
        res = self.client.post(
            "/api/user/",
            {
                "username": "attacker",
                "password": "Passw0rd123",
                "email": "attacker@example.com",
                "is_superuser": True,
                "is_staff": True,
                "role": "superadmin",
            },
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="attacker")
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertEqual(user.role, User.Role.OWNER)

    def test_registration_response_never_includes_password(self):
        res = self.client.post(
            "/api/user/",
            {"username": "someone", "password": "Passw0rd123", "email": "someone@example.com"},
        )
        self.assertNotIn("password", res.data)


class CookieAuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cookieuser", password="Passw0rd123")

    def test_login_sets_httponly_cookies_and_no_tokens_in_body(self):
        res = self.client.post(
            "/api/auth/login/", {"username": "cookieuser", "password": "Passw0rd123"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn("access", res.data)
        self.assertNotIn("refresh", res.data)

        access_cookie = res.cookies.get("access_token")
        refresh_cookie = res.cookies.get("refresh_token")
        self.assertIsNotNone(access_cookie)
        self.assertIsNotNone(refresh_cookie)
        self.assertTrue(access_cookie["httponly"])
        self.assertTrue(refresh_cookie["httponly"])

    def test_authenticated_request_works_via_cookie(self):
        self.client.post("/api/auth/login/", {"username": "cookieuser", "password": "Passw0rd123"})
        res = self.client.get("/api/user/me/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["username"], "cookieuser")

    def test_logout_revokes_session(self):
        self.client.post("/api/auth/login/", {"username": "cookieuser", "password": "Passw0rd123"})
        logout_res = self.client.post("/api/auth/logout/")
        self.assertEqual(logout_res.status_code, status.HTTP_204_NO_CONTENT)

        me_res = self.client.get("/api/user/me/")
        self.assertEqual(me_res.status_code, status.HTTP_401_UNAUTHORIZED)
