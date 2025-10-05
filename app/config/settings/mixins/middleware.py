from typing import List

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class MiddlewareSettingsMixin(BaseSettings):

    # Custom middleware to add
    CUSTOM_MIDDLEWARE: List[str] = Field(default_factory=list)

    # Security middleware options
    MIDDLEWARE_ENABLE_SECURITY: bool = Field(default=True)
    MIDDLEWARE_ENABLE_CORS: bool = Field(default=True)

    @computed_field
    @property
    def MIDDLEWARE(self) -> List[str]:
        """Django MIDDLEWARE configuration."""
        middleware = []

        # Security middleware (should be first)
        if self.MIDDLEWARE_ENABLE_SECURITY:
            middleware.append("django.middleware.security.SecurityMiddleware")

        # Core Django middleware
        middleware.extend(
            [
                "django.contrib.sessions.middleware.SessionMiddleware",
            ]
        )

        # CORS middleware (before CommonMiddleware)
        if self.MIDDLEWARE_ENABLE_CORS:
            middleware.append("corsheaders.middleware.CorsMiddleware")

        # Continue with core middleware
        middleware.extend(
            [
                "django.middleware.common.CommonMiddleware",
                "django.middleware.csrf.CsrfViewMiddleware",
                "django.contrib.auth.middleware.AuthenticationMiddleware",
                "django.contrib.messages.middleware.MessageMiddleware",
                "django.middleware.clickjacking.XFrameOptionsMiddleware",
            ]
        )

        # Add custom middleware at the end
        middleware.extend(self.CUSTOM_MIDDLEWARE)

        return middleware
