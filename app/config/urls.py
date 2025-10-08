from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from app.api import api

from .settings.main import get_settings

settings = get_settings()

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
