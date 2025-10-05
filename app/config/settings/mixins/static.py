# app/config/settings/components/static.py
"""Static files settings mixin."""

from __future__ import annotations

from typing import List

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class StaticFilesSettingsMixin(BaseSettings):
    """Static files configuration mixin."""

    STATIC_URL: str = Field(default="/static/")
    MEDIA_URL: str = Field(default="/media/")

    @computed_field
    @property
    def STATIC_ROOT(self) -> str:
        """Static files root directory."""
        return str(self.APP_DIR / "staticfiles")

    @computed_field
    @property
    def MEDIA_ROOT(self) -> str:
        """Media files root directory."""
        return str(self.APP_DIR / "media")

    @computed_field
    @property
    def STATICFILES_DIRS(self) -> List[str]:
        """Additional static files directories."""
        dirs = []
        common_static = self.APP_DIR / "static"
        if common_static.exists():
            dirs.append(str(common_static))
        return dirs

    @computed_field
    @property
    def STATICFILES_FINDERS(self) -> List[str]:
        return [
            "django.contrib.staticfiles.finders.FileSystemFinder",
            "django.contrib.staticfiles.finders.AppDirectoriesFinder",
        ]

    @computed_field
    @property
    def STATICFILES_STORAGE(self) -> str:
        if not self.DEBUG:
            return "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
        return "django.contrib.staticfiles.storage.StaticFilesStorage"
