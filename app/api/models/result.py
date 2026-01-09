from django.db import models
from django.conf import settings
from pathlib import Path

from app.api.models.mixins import UUIDPrimaryKeyModelMixin, TimeStampedModelMixin
from app.api.constants.odm import ODMTaskResultType
from app.api.models.workspace import Workspace


def result_file_upload_path(instance, filename):
    return str(Path(settings.RESULTS_DIR_NAME) / str(instance.workspace.uuid) / filename)


class ODMTaskResult(UUIDPrimaryKeyModelMixin, TimeStampedModelMixin, models.Model):
    result_type = models.CharField(
        choices=ODMTaskResultType.choices(),
    )
    workspace = models.ForeignKey(
        Workspace,
        related_name="results",
        on_delete=models.CASCADE,
    )
    file = models.FileField(upload_to=result_file_upload_path)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_result_type_display()} ({self.uuid})"

    @property
    def odm_result_type(self) -> ODMTaskResultType:
        return ODMTaskResultType(self.result_type)
