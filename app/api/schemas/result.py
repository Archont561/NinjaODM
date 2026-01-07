from uuid import UUID

from pydantic import Field
from ninja import ModelSchema

from app.api.models.result import ODMTaskResult


class ResultResponse(ModelSchema):
    workspace_uuid: UUID = Field(..., alias="workspace.uuid")

    class Meta:
        model = ODMTaskResult
        fields = ["uuid", "result_type", "created_at"]
