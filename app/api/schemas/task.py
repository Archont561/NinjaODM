from typing import Optional, Any, Dict
from uuid import UUID
from ninja import ModelSchema, Schema, FilterSchema
from pydantic import Field, field_validator, BaseModel
from datetime import datetime

from app.api.models.task import ODMTask
from app.api.schemas.odm_option import ODMOptionsInternal, ODMOptionsPublic
from app.api.constants.odm import ODMTaskStatus, ODMProcessingStage, NodeODMTaskStatus


class CreateTaskInternal(Schema):
    name: str
    options: ODMOptionsInternal


class CreateTaskPublic(Schema):
    name: str
    options: ODMOptionsPublic


class UpdateTaskInternal(Schema):
    options: Optional[ODMOptionsPublic] = None
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

    @field_validator("status", mode="before")
    @classmethod
    def parse_status_enum_from_string(cls, v: Any) -> Any:
        if isinstance(v, str):
            normalized_name = v.strip().replace(" ", "_").upper()
            if v.isdigit():
                return int(v)

            try:
                return ODMTaskStatus[normalized_name].value
            except KeyError:
                pass

            raise ValueError(
                f"Invalid Task Status Type: '{v}'. Accepted values: {[e.label for e in ODMTaskStatus]}"
            )

        return v

    @field_validator("step", mode="before")
    @classmethod
    def parse_step_enum_from_string(cls, v: Any) -> Any:
        if isinstance(v, str):
            normalized_name = v.strip().replace(" ", "_").upper()
            if v.isdigit():
                return int(v)

            try:
                return ODMProcessingStage[normalized_name].value
            except KeyError:
                pass

            raise ValueError(
                f"Invalid Task Status Type: '{v}'. Accepted values: {[e.label for e in ODMProcessingStage]}"
            )

        return v
