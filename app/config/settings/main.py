from pathlib import Path
from functools import cache

from .mixins import (
    AppsSettingsMixin,
    AuthSettingsMixin,
    CacheSettingsMixin,
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
    CoreSettingsMixin,
)


APP_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_DIR = APP_DIR.parent


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
):
    """
    Complete Django settings using multiple inheritance.

    Settings are composed from various mixins, each handling a specific
    aspect of Django configuration. All settings are automatically
    exported to Django's expected format.
    """

    APP_DIR: Path = APP_DIR
    PROJECT_DIR: Path = PROJECT_DIR

    model_config = {
        'env_file': PROJECT_DIR / '.env',
        'env_file_encoding': 'utf-8',
        'case_sensitive': True,
        'extra': 'ignore',
    }

    def model_post_init(self, __context) -> None:
        """Post-initialization ho   ok."""
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        directories = [
            self.STATIC_ROOT,
            self.MEDIA_ROOT,
        ]

        for directory in directories:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
            except IOError:
                pass  # Ignore errors during directory creation

@cache
def get_settings() -> PydanticDjangoSettings:
    return PydanticDjangoSettings() # noqa