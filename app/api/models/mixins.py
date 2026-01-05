import uuid
from django.db import models
from django.utils import timezone


class UUIDPrimaryKeyModelMixin(models.Model):
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    class Meta:
        abstract = True


class TimeStampedModelMixin(models.Model):
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True
