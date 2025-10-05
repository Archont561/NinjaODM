from typing import List

from pydantic import computed_field
from pydantic_settings import BaseSettings


class AppsSettingsMixin(BaseSettings):

    @computed_field
    @property
    def INSTALLED_APPS(self) -> List[str]:
        return [
            # Django core
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'django.contrib.gis',
        ] + [
            # Third party
            'corsheaders',
            'ninja_extra',
            'ninja_jwt',
            'ninja_jwt.token_blacklist',
        ] + [
            # Local apps
            'core',
        ]
        return (
            [
                # Django core
                "django.contrib.admin",
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django.contrib.messages",
                "django.contrib.staticfiles",
                "django.contrib.gis",
            ]
            + [
                # Third party
                "corsheaders",
                "ninja_extra",
                "ninja_jwt",
                "ninja_jwt.token_blacklist",
            ]
            + [
                # Local apps
            ]
        )
