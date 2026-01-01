from django.contrib import admin
from django.urls import path

from app.api import create_api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", create_api().urls),
]
