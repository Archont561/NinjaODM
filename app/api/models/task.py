from django.db import models
from django.conf import settings
from pathlib import Path

from app.api.models.mixins import UUIDPrimaryKeyModelMixin, TimeStampedModelMixin
from app.api.constants.odm import ODMTaskStatus, ODMProcessingStage
from app.api.models.workspace import Workspace


class ODMTask(UUIDPrimaryKeyModelMixin, TimeStampedModelMixin, models.Model):
    status = models.IntegerField(
        choices=ODMTaskStatus.choices(),
        default=ODMTaskStatus.QUEUED.value,
    )
    step = models.IntegerField(
        choices=ODMProcessingStage.choices(),
        default=ODMProcessingStage.DATASET.value,
    )
    options = models.JSONField(default=dict, blank=True)
    workspace = models.ForeignKey(
        Workspace,
        related_name="tasks",
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ODMTask {self.uuid} ({self.get_status_display()} @ {self.get_step_display()})"

    @property
    def odm_status(self) -> ODMTaskStatus:
        return ODMTaskStatus(self.status)

    @property
    def odm_step(self) -> ODMProcessingStage:
        return ODMProcessingStage(self.step)

    @property
    def task_dir(self) -> Path:
        """
        /<TASKS_DIR>/{workspace_uuid}/{task_uuid} under the workspace.
        """
        return Path(getattr(settings, "TASKS_DIR")) / str(self.workspace.uuid) / str(self.uuid)

    def get_current_step_options(self) -> dict:
        return self.options.get(self.step, {})