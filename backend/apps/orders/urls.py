from django.urls import path
from . import views

urlpatterns = [
    path("", views.OrderListAPIView.as_view()),
    path("<int:pk>/", views.OrderDetailAPIView.as_view()),
]
