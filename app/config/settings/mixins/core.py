from typing import List

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings
from enum import StrEnum


class AppEnvironment(StrEnum):
    PRODUCTION = "prod"
    DEVELOPMENT = "dev"
    STAGING = "staging"
    TESTING = "test"


class CoreSettingsMixin(BaseSettings):

    # Required settings
    ENVIRONMENT: AppEnvironment = Field(default=AppEnvironment.DEVELOPMENT)
    SECRET_KEY: SecretStr = Field(..., min_length=30, alias="DJANGO_SECRET_KEY")
    ALLOWED_HOSTS: List[str] = Field(default_factory=list)

    # Django configuration
    ROOT_URLCONF: str = 'config.urls'
    WSGI_APPLICATION: str = 'config.wsgi.application'
    ASGI_APPLICATION: str = 'config.asgi.application'
    DEFAULT_AUTO_FIELD: str = 'django.db.models.BigAutoField'


    @computed_field
    @property
    def DEBUG(self) -> bool:
        return self.DEV or self.TEST

    @computed_field
    @property
    def DEV(self) -> bool:
        return self.ENVIRONMENT == AppEnvironment.DEVELOPMENT

    @computed_field
    @property
    def TEST(self) -> bool:
        return self.ENVIRONMENT == AppEnvironment.TESTING

    @computed_field
    @property
    def STAGING(self) -> bool:
        return self.ENVIRONMENT == AppEnvironment.STAGING

    @computed_field
    @property
    def PROD(self) -> bool:
        return self.ENVIRONMENT == AppEnvironment.PRODUCTION
