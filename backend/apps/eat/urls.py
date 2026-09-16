from django.urls import path
from . import views

urlpatterns = [
    path("", views.EatListCreateAPIView.as_view()),
    path("<int:pk>/", views.EatDetailAPIView.as_view()),
    path("check-model/<int:pk>/", views.CheckTaskAPIView.as_view()),
    path("regenerate-model/<int:pk>/", views.RegenerateModelAPIView.as_view()),
    path("regenerate-usdz/<int:pk>/", views.RegenerateUSDZAPIView.as_view()),
    path("category/", views.CategoryListCreateAPIView.as_view()),
    path("category/<int:pk>/", views.CategoryDetailAPIView.as_view()),
]
