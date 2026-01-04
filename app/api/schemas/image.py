from uuid import UUID
from typing import Optional
from pydantic import Field
from ninja import ModelSchema

from app.api.models.image import Image


class ImageResponse(ModelSchema):
    workspace_uuid: UUID = Field(..., alias="workspace.uuid")
    image_url: Optional[str]

    class Meta:
        model = Image
        fields = ["uuid", "is_thumbnail", "created_at"]

    @staticmethod
    def resolve_image_url(obj: Image):
        return obj.image_file.url if obj.image_file else None
    