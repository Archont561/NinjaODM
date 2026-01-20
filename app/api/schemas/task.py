from typing import Optional, Any, Dict
from uuid import UUID
from ninja import ModelSchema, Schema, FilterSchema
from pydantic import Field, field_validator, BaseModel
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
    status: Optional[ODMTaskStatus] = Field(None, q="status")
    step: Optional[ODMProcessingStage] = Field(None, q="step")
    created_after: Optional[datetime] = Field(None, q="created_at__gte")
    created_before: Optional[datetime] = Field(None, q="created_at__lte")
    workspace_uuid: Optional[UUID] = Field(None, q="workspace__uuid")
