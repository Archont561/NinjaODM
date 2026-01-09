import random
import string
from django.db import models
from django.conf import settings
from pathlib import Path

from app.api.models.mixins import UUIDPrimaryKeyModelMixin, TimeStampedModelMixin
from app.api.constants.odm import ODMTaskStatus, ODMProcessingStage
from app.api.models.workspace import Workspace


def generate_task_name():
    adjectives = [
        "Quick",
        "Silent",
        "Smart",
        "Brave",
        "Bright",
        "Swift",
        "Calm",
        "Bold",
        "Clever",
        "Lucky",
    ]
    nouns = [
        "Task",
        "Process",
        "Job",
        "Runner",
        "Worker",
        "Agent",
        "Handler",
        "Executor",
        "Service",
    ]

    random_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    return f"{random.choice(adjectives)}{random.choice(nouns)}-{random_suffix}"


class ODMTask(UUIDPrimaryKeyModelMixin, TimeStampedModelMixin, models.Model):
    name = models.CharField(
        max_length=50,
        default=generate_task_name,
    )
    status = models.CharField(
        choices=ODMTaskStatus.choices(),
        default=ODMTaskStatus.QUEUED.value,
    )
    step = models.CharField(
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
        return Path(settings.TASKS_DIR) / str(self.uuid)

    def get_current_step_options(self) -> dict:
        return self.options.get(self.step, {})
