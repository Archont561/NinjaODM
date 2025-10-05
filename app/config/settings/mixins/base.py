from enum import StrEnum
from pathlib import Path

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(__file__).resolve().parent.parent.parent.parent
PROJECT_DIR = APP_DIR.parent


class AppEnvironment(StrEnum):
    PRODUCTION = "prod"
    DEVELOPMENT = "dev"
    STAGING = "staging"
    TESTING = "test"


class BaseSettingsMixin(BaseSettings):
    APP_DIR: Path = APP_DIR
    PROJECT_DIR: Path = PROJECT_DIR

    model_config = SettingsConfigDict(
        env_file=PROJECT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        enable_decoding=False,
    )

    ENVIRONMENT: AppEnvironment = Field(default=AppEnvironment.DEVELOPMENT)
    SECRET_KEY: SecretStr = Field(..., min_length=30, alias="DJANGO_SECRET_KEY")

    @computed_field
    @property
    def DATA_DIR(self) -> Path:
        return self.APP_DIR / "data"

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
