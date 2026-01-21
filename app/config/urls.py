from django.urls import path, include
from django.shortcuts import redirect


urlpatterns = [
    path("", lambda _: redirect("/api/docs")),
    path("api/", include("app.api.urls")),
]
