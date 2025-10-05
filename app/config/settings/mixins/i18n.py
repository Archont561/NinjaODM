from typing import List

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class I18nSettingsMixin(BaseSettings):

    LANGUAGE_CODE: str = Field(default='en-us', alias='I18N_LANGUAGE_CODE')
    TIME_ZONE: str = Field(default='UTC', alias='I18N_TIME_ZONE')
    USE_I18N: bool = Field(default=True, alias='I18N_USE_I18N')
    USE_TZ: bool = Field(default=True, alias='I18N_USE_TZ')

    @computed_field
    @property
    def LOCALE_PATHS(self) -> List[str]:
        locale_dir = self.APP_DIR / 'locale'
        if locale_dir.exists():
            return [str(locale_dir)]
        return []

    @computed_field
    @property
    def LANGUAGES(self) -> List[tuple[str, str]]:
        return [
            ('en', 'English'),
            ('es', 'Spanish'),
            ('fr', 'French'),
            ('de', 'German'),
        ]