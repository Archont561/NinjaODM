from pydantic import Field, computed_field, SecretStr
from pydantic_settings import BaseSettings
from pathlib import Path
from enum import StrEnum


APP_DIR = Path(__file__).resolve().parent.parent.parent.parent
PROJECT_DIR = APP_DIR.parent


class AppEnvironment(StrEnum):
    PRODUCTION = "prod"
    DEVELOPMENT = "dev"
    STAGING = "staging"
    TESTING = "test"


class BaseSettingsMixin(BaseSettings):
    APP_DIR: Path = APP_DIR
    PROJECT_DIR: Path = APP_DIR.parent

    model_config = {
        "env_file": PROJECT_DIR / ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }

    ENVIRONMENT: AppEnvironment = Field(default=AppEnvironment.DEVELOPMENT)
    SECRET_KEY: SecretStr = Field(..., min_length=30, alias="DJANGO_SECRET_KEY")

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