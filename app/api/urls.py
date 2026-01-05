from django.urls import path
from .api import create_api


urlpatterns = [
    path("", create_api().urls),
]
