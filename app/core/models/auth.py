from django.db import models


class AuthorizedService(models.Model):
    name = models.CharField(max_length=100)
    api_key = models.CharField(max_length=128, unique=True)
    api_secret = models.CharField(max_length=128)
    allowed_scopes = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
