from django.urls import path
from . import views

urlpatterns = [
    path("", views.TableListCreateAPIView.as_view()),
    path("<int:pk>/", views.TableDetailAPIView.as_view()),
]