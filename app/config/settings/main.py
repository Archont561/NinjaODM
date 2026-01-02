from functools import cache
from pathlib import Path
from typing import List, Union

from .mixins import (
    AppsSettingsMixin,
    AuthSettingsMixin,
    CacheSettingsMixin,
    CoreSettingsMixin,
    DatabaseSettingsMixin,
    EmailSettingsMixin,
    GISSettingsMixin,
    I18nSettingsMixin,
    JWTSettingsMixin,
    LoguruSettingsMixin,
    MiddlewareSettingsMixin,
    SecuritySettingsMixin,
    StaticFilesSettingsMixin,
    TemplatesSettingsMixin,
    ODMSettingsMixin,
)


class PydanticDjangoSettings(
    CoreSettingsMixin,
    AppsSettingsMixin,
    DatabaseSettingsMixin,
    CacheSettingsMixin,
    StaticFilesSettingsMixin,
    MiddlewareSettingsMixin,
    TemplatesSettingsMixin,
    AuthSettingsMixin,
    SecuritySettingsMixin,
    I18nSettingsMixin,
    EmailSettingsMixin,
    LoguruSettingsMixin,
    GISSettingsMixin,
    JWTSettingsMixin,
    ODMSettingsMixin,
):
    """
    Complete Django settings using multiple inheritance.

    Settings are composed from various mixins, each handling a specific
    aspect of Django configuration. All settings are automatically
    exported to Django's expected format.
    """

    def model_post_init(self, __context, /) -> None:
        """Post-initialization ho   ok."""
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        directories: List[Union[str, Path]] = [
            self.STATIC_ROOT,
            self.MEDIA_ROOT,
            self.DATA_DIR,
            self.WORKSPACES_DIR,
        ]

        for directory in directories:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
            except IOError:
                pass  # Ignore errors during directory creation


@cache
def get_settings() -> PydanticDjangoSettings:
    return PydanticDjangoSettings()  # noqa
