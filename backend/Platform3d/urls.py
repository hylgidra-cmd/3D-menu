from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
)
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.table.views import PublicTableMenuAPIView
from apps.user.auth_views import CookieTokenObtainPairView, CookieTokenRefreshView, LogoutView

# handler404 = 'apps.user.views.custom_404'

urlpatterns = [
    # Plain Django view (bypasses DRF auth/throttling) for Docker/Caddy healthchecks.
    path("health/", lambda request: JsonResponse({"status": "ok"})),

    path("admin/", admin.site.urls),
    path("api/user/", include("apps.user.urls")),
    path("api/restaurant/", include("apps.restaurant.urls")),
    path("api/table/", include("apps.table.urls")),
    path("api/eat/", include("apps.eat.urls")),
    path("api/public/menu/<uuid:token>/", PublicTableMenuAPIView.as_view()),

    # httpOnly-cookie auth flow, used by the admin/super-admin browser apps.
    path("api/auth/login/", CookieTokenObtainPairView.as_view()),
    path("api/auth/refresh/", CookieTokenRefreshView.as_view()),
    path("api/auth/logout/", LogoutView.as_view()),

    # Header-based JWT (Authorization: Bearer ...), kept for non-browser API clients.
    path("api/token/", TokenObtainPairView.as_view()),
    path("api/refresh/", TokenRefreshView.as_view()),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)