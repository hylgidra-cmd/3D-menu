from django.urls import path
from . import views

urlpatterns = [
    path("", views.UserListCreateAPIView.as_view()),
    path("<int:pk>/", views.UserDetailAPIView.as_view()),
    path("me/", views.MeAPIView.as_view()),
]