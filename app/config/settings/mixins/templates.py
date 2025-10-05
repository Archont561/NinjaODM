from typing import Any, Dict, List

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class TemplatesSettingsMixin(BaseSettings):
    """Templates configuration mixin."""

    TEMPLATES_BACKEND: str = Field(
        default='django.template.backends.django.DjangoTemplates',
    )
    TEMPLATES_APP_DIRS: bool = Field(default=True)

    @computed_field
    @property
    def TEMPLATES(self) -> List[Dict[str, Any]]:
        """Django TEMPLATES configuration."""
        # Check for templates directory
        templates_dir = self.APP_DIR / 'templates'
        template_dirs = []
        if templates_dir.exists():
            template_dirs.append(str(templates_dir))

        return [
            {
                'BACKEND': self.TEMPLATES_BACKEND,
                'DIRS': template_dirs,
                'APP_DIRS': self.TEMPLATES_APP_DIRS,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.debug',
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                        'django.template.context_processors.i18n',
                        'django.template.context_processors.media',
                        'django.template.context_processors.static',
                        'django.template.context_processors.tz',
                    ],
                },
            }
        ]