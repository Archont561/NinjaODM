from typing import Optional

from pydantic import Field
from .base import BaseSettingsMixin


class EmailSettingsMixin(BaseSettingsMixin):

    # Email backend
    EMAIL_BACKEND: str = Field(default="django.core.mail.backends.console.EmailBackend")

    # SMTP settings
    EMAIL_HOST: str = Field(default="localhost")
    EMAIL_PORT: int = Field(default=25)
    EMAIL_USE_TLS: bool = Field(default=False)
    EMAIL_USE_SSL: bool = Field(default=False)
    EMAIL_TIMEOUT: Optional[int] = Field(default=None)

    # Authentication
    EMAIL_HOST_USER: str = Field(default="")
    EMAIL_HOST_PASSWORD: str = Field(default="")

    # Email addresses
    DEFAULT_FROM_EMAIL: str = Field(default="webmaster@localhost")
    SERVER_EMAIL: str = Field(default="root@localhost")

    # Additional settings
    EMAIL_SUBJECT_PREFIX: str = Field(default="[NinjaODM] ")
