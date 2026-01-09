from typing import Optional, Any
from uuid import UUID
from datetime import datetime
from pydantic import Field, field_validator
from ninja import ModelSchema, FilterSchema

from app.api.models.result import ODMTaskResult
from app.api.constants.odm import ODMTaskResultType


class ResultResponse(ModelSchema):
    workspace_uuid: UUID = Field(..., alias="workspace.uuid")
    result_type: ODMTaskResult

    class Meta:
        model = ODMTaskResult
        fields = ["uuid", "created_at"]


class ResultFilterSchema(FilterSchema):
    result_type: Optional[ODMTaskResultType] = Field(None, q="result_type")
    created_after: Optional[datetime] = Field(None, q="created_at__gte")
    created_before: Optional[datetime] = Field(None, q="created_at__lte")

    @field_validator("result_type", mode="before")
    @classmethod
    def parse_enum_from_string(cls, v: Any) -> Any:
        if isinstance(v, str):
            normalized_name = v.strip().replace(" ", "_").upper()
            if v.isdigit():
                return int(v)

            try:
                return ODMTaskResultType[normalized_name].value
            except KeyError:
                pass

            raise ValueError(
                f"Invalid Result Type: '{v}'. Accepted values: {[e.label for e in ODMTaskResultType]}"
            )

        return v
