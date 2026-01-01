from django.db import models
import secrets


def generate_api_key() -> str:
    return "svc_" + secrets.token_urlsafe(32)[:40]


def generate_api_secret() -> str:
    return secrets.token_hex(32)


class AuthorizedService(models.Model):
    name = models.CharField(max_length=100)

    api_key = models.CharField(
        max_length=128,
        unique=True,
        default=generate_api_key,
        editable=False,
    )

    api_secret = models.CharField(
        max_length=128,
        default=generate_api_secret,
        editable=False,
    )

    allowed_scopes = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name
