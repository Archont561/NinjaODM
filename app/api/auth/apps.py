from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.api.auth"
    verbose_name = "Authentication and Authorization"
