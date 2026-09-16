from django.urls import path
from . import views

urlpatterns = [
    path("", views.RestaurantListCreateAPIView.as_view()),
    path("mine/", views.MyRestaurantsAPIView.as_view()),
    path("platform-stats/", views.PlatformStatsAPIView.as_view()),
    path("<int:pk>/", views.RestaurantDetailAPIView.as_view()),
    path("<int:pk>/activate/", views.RestaurantActivationAPIView.as_view()),
]
