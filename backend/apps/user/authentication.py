from rest_framework_simplejwt.authentication import JWTAuthentication
from .cookies import ACCESS_COOKIE_NAME


class CookieJWTAuthentication(JWTAuthentication):
    """
    JWT auth that reads the access token from an httpOnly cookie.
    Falls back to the standard `Authorization: Bearer` header so non-browser
    API clients (scripts, a future mobile app) keep working unchanged.
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        raw_token = request.COOKIES.get(ACCESS_COOKIE_NAME)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
