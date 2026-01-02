from django.urls import path
from app.api.api import create_api


urlpatterns = [
    path("api/", create_api().urls),
]
