from typing import List

from pydantic import Field, field_validator

from .base import BaseSettingsMixin


class CoreSettingsMixin(BaseSettingsMixin):

    ALLOWED_HOSTS: List[str] = Field(default=["localhost", "127.0.0.1"])

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def split_csv_to_list(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]

        if isinstance(v, list):
            return v

        raise ValueError(
            f"ALLOWED_HOSTS must be comma separated string or list or strings, not {v}!"
        )

    ROOT_URLCONF: str = "app.core.urls"
    WSGI_APPLICATION: str = "app.config.wsgi.application"
    ASGI_APPLICATION: str = "app.config.asgi.application"
    DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"
