from typing import List

from pydantic import Field
from .base import BaseSettingsMixin


class SecuritySettingsMixin(BaseSettingsMixin):
    # CSRF Protection
    CSRF_COOKIE_SECURE: bool = Field(default=False)
    CSRF_COOKIE_HTTPONLY: bool = Field(default=True)
    CSRF_COOKIE_SAMESITE: str = Field(default="Lax")
    CSRF_TRUSTED_ORIGINS: List[str] = Field(default_factory=list)

    # Session Security
    SESSION_COOKIE_SECURE: bool = Field(default=False)
    SESSION_COOKIE_HTTPONLY: bool = Field(default=True)
    SESSION_COOKIE_SAMESITE: str = Field(default="Lax")
    SESSION_COOKIE_AGE: int = Field(default=1209600)  # 2 weeks
    SESSION_ENGINE: str = Field(
        default="django.contrib.sessions.backends.db",
    )

    # HTTPS/SSL
    SECURE_SSL_REDIRECT: bool = Field(default=False)
    SECURE_HSTS_SECONDS: int = Field(default=0)
    SECURE_HSTS_INCLUDE_SUBDOMAINS: bool = Field(default=False)
    SECURE_HSTS_PRELOAD: bool = Field(default=False)

    # Security Headers
    SECURE_BROWSER_XSS_FILTER: bool = Field(default=True)
    SECURE_CONTENT_TYPE_NOSNIFF: bool = Field(default=True)
    X_FRAME_OPTIONS: str = Field(default="DENY")

    # CORS
    CORS_ALLOWED_ORIGINS: List[str] = Field(default_factory=list)
    CORS_ALLOW_ALL_ORIGINS: bool = Field(default=False)
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    CORS_ALLOW_HEADERS: List[str] = Field(
        default_factory=lambda: [
            "accept",
            "authorization",
            "content-type",
            "user-agent",
            "x-csrftoken",
            "x-requested-with",
        ]
    )
