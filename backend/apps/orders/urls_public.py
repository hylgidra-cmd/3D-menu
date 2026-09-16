from django.urls import path
from .views import PublicOrderCreateAPIView

urlpatterns = [path("", PublicOrderCreateAPIView.as_view())]
