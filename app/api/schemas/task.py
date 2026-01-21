from typing import Optional, Any, Dict, Annotated
from uuid import UUID
from ninja import ModelSchema, Schema, FilterSchema, FilterLookup
from pydantic import Field, BaseModel
from datetime import datetime

from app.api.models.task import ODMTask
from app.api.constants.odm import (
    ODMTaskStatus,
    ODMProcessingStage,
    NodeODMTaskStatus,
    ODMQualityOption,
)


class CreateTask(Schema):
    name: str
    quality: ODMQualityOption = ODMQualityOption.ULTRA_LOW


class UpdateTaskInternal(Schema):
    status: Optional[ODMTaskStatus] = None
    step: Optional[ODMProcessingStage] = None


class ODMTaskWebhookStatus(BaseModel):
    code: NodeODMTaskStatus


class ODMTaskWebhookInternal(Schema):
    uuid: UUID
    name: str
    dateCreated: int
    processingTime: float
    status: ODMTaskWebhookStatus
    options: Dict[str, Any]
    imagesCount: int
    progress: int


class TaskResponse(ModelSchema):
    workspace_uuid: UUID = Field(..., alias="workspace.uuid")
    status: ODMTaskStatus
    step: ODMProcessingStage

    class Meta:
        model = ODMTask
        fields = [
            "uuid",
            "options",
            "created_at",
            "step",
            "status",
        ]


class TaskFilterSchema(FilterSchema):
    status: Annotated[Optional[ODMTaskStatus], FilterLookup("status")] = None
    step: Annotated[Optional[ODMProcessingStage], FilterLookup("step")] = None
    created_after: Annotated[Optional[datetime], FilterLookup("created_at__gte")] = None
    created_before: Annotated[Optional[datetime], FilterLookup("created_at__lte")] = (
        None
    )
    workspace_uuid: Annotated[Optional[UUID], FilterLookup("workspace__uuid")] = None


class TaskBaseSSEData(Schema):
    uuid: UUID
    status: str
    step: str


class TaskCreatedSSEData(TaskBaseSSEData): ...


class TaskUpdatedSSEData(TaskBaseSSEData): ...


class TaskDeletedSSEData(TaskBaseSSEData): ...


class TaskPausedSSEData(TaskBaseSSEData): ...


class TaskResumedSSEData(TaskBaseSSEData): ...


class TaskCancelledSSEData(TaskBaseSSEData): ...


class TaskNextStageSSEData(TaskBaseSSEData): ...


class TaskStartedSSEData(TaskBaseSSEData): ...


class TaskCompletedSSEData(TaskBaseSSEData): ...


class TaskFailedSSEData(TaskBaseSSEData):
    error: str | None = None
