from typing import Any, Dict

from pydantic import Field, computed_field
from .base import BaseSettingsMixin


class CelerySettingsMixin(BaseSettingsMixin):

    @computed_field
    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.CACHE_LOCATION
        
    @computed_field
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self.CACHE_LOCATION
