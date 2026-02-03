from typing import Optional, Annotated
from uuid import UUID
from datetime import datetime
from pydantic import Field
from ninja import ModelSchema, FilterSchema, FilterLookup, Schema

from app.api.models.image import Image


class ImageResponse(ModelSchema):
    workspace_uuid: UUID = Field(..., alias="workspace.uuid")

    class Meta:
        model = Image
        fields = ["uuid", "name", "is_thumbnail", "created_at"]


class ImageFilterSchema(FilterSchema):
    name: Annotated[Optional[str], FilterLookup("name__icontains")] = None  
    is_thumbnail: Annotated[Optional[bool], FilterLookup("is_thumbnail")] = None
    created_after: Annotated[Optional[datetime], FilterLookup("created_at__gte")] = None
    created_before: Annotated[Optional[datetime], FilterLookup("created_at__lte")] = None
    workspace_uuid: Annotated[Optional[UUID], FilterLookup("workspace__uuid")] = None


class ImageBaseSSEData(Schema):
    uuid: UUID
    name: str


class ImageDeletedSSEData(ImageBaseSSEData): ...
