from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import Field
from ninja import ModelSchema, FilterSchema

from app.api.models.image import Image


class ImageResponse(ModelSchema):
    workspace_uuid: UUID = Field(..., alias="workspace.uuid")

    class Meta:
        model = Image
        fields = ["uuid", "name", "is_thumbnail", "created_at"]


class ImageFilterSchema(FilterSchema):
    name: Optional[str] = Field(None, q="name__icontains")
    is_thumbnail: Optional[bool] = Field(None, q="is_thumbnail")
    created_after: Optional[datetime] = Field(None, q="created_at__gte")
    created_before: Optional[datetime] = Field(None, q="created_at__lte")
