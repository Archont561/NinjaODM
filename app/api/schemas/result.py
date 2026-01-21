from typing import Optional, Annotated
from uuid import UUID
from datetime import datetime
from pydantic import Field
from ninja import ModelSchema, FilterSchema, FilterLookup

from app.api.models.result import ODMTaskResult
from app.api.constants.odm import ODMTaskResultType


class ResultResponse(ModelSchema):
    workspace_uuid: UUID = Field(..., alias="workspace.uuid")
    result_type: ODMTaskResultType

    class Meta:
        model = ODMTaskResult
        fields = ["uuid", "created_at"]


class ResultFilterSchema(FilterSchema):
    result_type: Annotated[Optional[ODMTaskResultType], FilterLookup("result_type")] = (
        None
    )
    created_after: Annotated[Optional[datetime], FilterLookup("created_at__gte")] = None
    created_before: Annotated[Optional[datetime], FilterLookup("created_at__lte")] = (
        None
    )
    workspace_uuid: Annotated[Optional[UUID], FilterLookup("workspace__uuid")] = None
