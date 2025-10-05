from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class CoreSettingsMixin(BaseSettings):

    ALLOWED_HOSTS: List[str] = Field(default=["localhost", "127.0.0.1"])

    ROOT_URLCONF: str = "app.config.urls"
    WSGI_APPLICATION: str = "app.config.wsgi.application"
    ASGI_APPLICATION: str = "app.config.asgi.application"
    DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"
