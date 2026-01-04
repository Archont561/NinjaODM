from uuid import UUID
from typing import Optional

from pydantic import Field
from ninja import ModelSchema, Schema

from app.api.models.result import ODMTaskResult


class ResultResponse(ModelSchema):
    workspace_uuid: UUID = Field(..., alias="workspace.uuid")
    file_url: Optional[str]

    class Meta:
        model = ODMTaskResult
        fields = ["uuid", "result_type", "created_at"]

    @staticmethod
    def resolve_file_url(obj: ODMTaskResult):
        return obj.file.url if obj.file else None
