import json
from typing import Any, Dict

from pydantic import Field, computed_field, field_validator
from .base import BaseSettingsMixin


class CacheSettingsMixin(BaseSettingsMixin):

    CACHE_BACKEND: str = Field(
        default="django.core.cache.backends.locmem.LocMemCache",
    )
    CACHE_LOCATION: str = Field(
        default="unique-snowflake",
    )
    CACHE_TIMEOUT: int = Field(default=300)
    CACHE_KEY_PREFIX: str = Field(default="ninjaodm")

    CACHE_OPTIONS: Dict[str, str] = Field(default_factory=dict)

    @field_validator("CACHE_OPTIONS", mode="before")
    @classmethod
    def parse_cache_options(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                raise ValueError("CACHE_OPTIONS must be valid JSON") from e
        return value

    @computed_field
    @property
    def CACHES(self) -> Dict[str, Any]:
        return {
            "default": {
                "BACKEND": self.CACHE_BACKEND,
                "LOCATION": self.CACHE_LOCATION,
                "TIMEOUT": self.CACHE_TIMEOUT,
                "KEY_PREFIX": self.CACHE_KEY_PREFIX,
                "OPTIONS": {
                    "MAX_ENTRIES": 300,
                    "CULL_FREQUENCY": 3,
                    **self.CACHE_OPTIONS,
                },
            }
        }
