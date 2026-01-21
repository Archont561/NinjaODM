from django.urls import path
from django.shortcuts import redirect
from .api import create_api


urlpatterns = [
    path("", lambda _: redirect("/api/docs")),
    path("", create_api().urls),
]
