from enum import StrEnum, auto

from datetime import timedelta
from typing import Any, Dict, List, Optional
from pydantic import Field, computed_field

from pydantic_settings import BaseSettings


class JWTAlgorithm(StrEnum):
    HS256 = auto()
    HS384 = auto()
    HS512 = auto()
    RS256 = auto()
    RS384 = auto()
    RS512 = auto()


class JWTSettingsMixin(BaseSettings):

    # Token lifetimes
    JWT_ACCESS_TOKEN_LIFETIME_MINUTES: int = Field(default=5, ge=1)
    JWT_REFRESH_TOKEN_LIFETIME_DAYS: int = Field(default=7, ge=1)
    JWT_SLIDING_TOKEN_LIFETIME_MINUTES: int = Field(default=5, ge=1)
    JWT_SLIDING_TOKEN_REFRESH_LIFETIME_DAYS: int = Field(default=7, ge=1)

    # Token rotation
    JWT_ROTATE_REFRESH_TOKENS: bool = Field(default=False)
    JWT_BLACKLIST_AFTER_ROTATION: bool = Field(default=False)
    JWT_UPDATE_LAST_LOGIN: bool = Field(default=False)

    # Algorithm
    JWT_ALGORITHM: JWTAlgorithm = Field(default=JWTAlgorithm.HS256)
    JWT_SIGNING_KEY: Optional[str] = Field(default=None)
    JWT_VERIFYING_KEY: Optional[str] = Field(default=None)

    # Claims
    JWT_AUDIENCE: Optional[str] = Field(default=None)
    JWT_ISSUER: Optional[str] = Field(default=None)
    JWT_JWK_URL: Optional[str] = Field(default=None)
    JWT_LEEWAY: int = Field(default=0)

    # Headers
    JWT_AUTH_HEADER_TYPES: List[str] = Field(default_factory=lambda: ["Bearer"])
    JWT_AUTH_HEADER_NAME: str = Field(default="HTTP_AUTHORIZATION")

    # User settings
    JWT_USER_ID_FIELD: str = Field(default="id")
    JWT_USER_ID_CLAIM: str = Field(default="user_id")

    # Token settings
    JWT_TOKEN_TYPE_CLAIM: str = Field(default="token_type")
    JWT_JTI_CLAIM: str = Field(default="jti")

    @computed_field
    @property
    def NINJA_JWT(self) -> Dict[str, Any]:
        """django-ninja-jwt configuration."""
        config: Dict[str, Any] = {
            # Token lifetimes
            "ACCESS_TOKEN_LIFETIME": timedelta(
                minutes=self.JWT_ACCESS_TOKEN_LIFETIME_MINUTES
            ),
            "REFRESH_TOKEN_LIFETIME": timedelta(
                days=self.JWT_REFRESH_TOKEN_LIFETIME_DAYS
            ),
            "SLIDING_TOKEN_LIFETIME": timedelta(
                minutes=self.JWT_SLIDING_TOKEN_LIFETIME_MINUTES
            ),
            "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(
                days=self.JWT_SLIDING_TOKEN_REFRESH_LIFETIME_DAYS
            ),
            # Rotation
            "ROTATE_REFRESH_TOKENS": self.JWT_ROTATE_REFRESH_TOKENS,
            "BLACKLIST_AFTER_ROTATION": self.JWT_BLACKLIST_AFTER_ROTATION,
            "UPDATE_LAST_LOGIN": self.JWT_UPDATE_LAST_LOGIN,
            # Algorithm
            "ALGORITHM": self.JWT_ALGORITHM,
            "SIGNING_KEY": self.JWT_SIGNING_KEY or self.SECRET_KEY.get_secret_value(),
            # Leeway
            "LEEWAY": self.JWT_LEEWAY,
            # Headers
            "AUTH_HEADER_TYPES": tuple(self.JWT_AUTH_HEADER_TYPES),
            "AUTH_HEADER_NAME": self.JWT_AUTH_HEADER_NAME,
            # User
            "USER_ID_FIELD": self.JWT_USER_ID_FIELD,
            "USER_ID_CLAIM": self.JWT_USER_ID_CLAIM,
            # Claims
            "TOKEN_TYPE_CLAIM": self.JWT_TOKEN_TYPE_CLAIM,
            "JTI_CLAIM": self.JWT_JTI_CLAIM,
            # Token classes
            "AUTH_TOKEN_CLASSES": ("ninja_jwt.tokens.AccessToken",),
            "TOKEN_USER_CLASS": "ninja_jwt.models.TokenUser",
        }

        # Optional settings
        if self.JWT_VERIFYING_KEY:
            config["VERIFYING_KEY"] = self.JWT_VERIFYING_KEY

        if self.JWT_AUDIENCE:
            config["AUDIENCE"] = self.JWT_AUDIENCE

        if self.JWT_ISSUER:
            config["ISSUER"] = self.JWT_ISSUER

        if self.JWT_JWK_URL:
            config["JWK_URL"] = self.JWT_JWK_URL

        return config
