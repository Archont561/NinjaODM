from typing import Any, Dict, List

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class AuthSettingsMixin(BaseSettings):

    # Password validation
    AUTH_MIN_PASSWORD_LENGTH: int = Field(default=8)
    AUTH_REQUIRE_UPPERCASE: bool = Field(default=True)
    AUTH_REQUIRE_LOWERCASE: bool = Field(default=True)
    AUTH_REQUIRE_DIGITS: bool = Field(default=True)
    AUTH_REQUIRE_SPECIAL_CHARS: bool = Field(default=False)

    @computed_field
    @property
    def PASSWORD_HASHERS(self) -> List[str]:
        """Password hashing algorithms."""
        return [
            "django.contrib.auth.hashers.Argon2PasswordHasher",
            "django.contrib.auth.hashers.PBKDF2PasswordHasher",
            "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
            "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
        ]

    @computed_field
    @property
    def AUTH_PASSWORD_VALIDATORS(self) -> List[Dict[str, Any]]:
        """Password validators configuration."""
        validators = [
            {
                "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
            },
            {
                "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
                "OPTIONS": {
                    "min_length": self.AUTH_MIN_PASSWORD_LENGTH,
                },
            },
            {
                "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
            },
            {
                "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
            },
        ]
        return validators
