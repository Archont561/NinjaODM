from typing import Any, Dict

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings
import dj_database_url


class DatabaseSettingsMixin(BaseSettings):

    DATABASE_URL: str = Field(...)

    @computed_field
    @property
    def DATABASES(self) -> Dict[str, Any]:
        return {
            "default": dj_database_url.parse(self.DATABASE_URL),
        }
