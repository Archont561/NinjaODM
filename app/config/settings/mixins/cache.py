from typing import Any, Dict

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class CacheSettingsMixin(BaseSettings):

    CACHE_BACKEND: str = Field(
        default='django.core.cache.backends.locmem.LocMemCache',
    )
    CACHE_LOCATION: str = Field(default='unique-snowflake', )
    CACHE_TIMEOUT: int = Field(default=300)
    CACHE_KEY_PREFIX: str = Field(default='ninjaodm')

    @computed_field
    @property
    def CACHES(self) -> Dict[str, Any]:
        """Django CACHES configuration."""
        return {
            'default': {
                'BACKEND': self.CACHE_BACKEND,
                'LOCATION': self.CACHE_LOCATION,
                'TIMEOUT': self.CACHE_TIMEOUT,
                'KEY_PREFIX': self.CACHE_KEY_PREFIX,
                'OPTIONS': {
                    'MAX_ENTRIES': 300,
                    'CULL_FREQUENCY': 3,
                }
            }
        }