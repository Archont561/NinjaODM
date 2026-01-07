from typing import List
from uuid import UUID
from django.http import FileResponse
from ninja import Query
from ninja_extra import (
    ModelControllerBase,
    ModelConfig,
    api_controller,
    http_get,
)

from app.api.auth.service import ServiceHMACAuth
from app.api.auth.user import ServiceUserJWTAuth
from app.api.models.image import Image
from app.api.permissions.image import IsImageOwner
from app.api.schemas.image import ImageResponse, ImageFilterSchema
from app.api.services.image import ImageModelService


@api_controller(
    "/images",
    auth=[ServiceUserJWTAuth()],
    permissions=[IsImageOwner],
    tags=["image", "public"],
)
class ImageControllerPublic(ModelControllerBase):
    service_type = ImageModelService
    model_config = ModelConfig(
        model=Image,
        retrieve_schema=ImageResponse,
        allowed_routes=["find_one", "delete"],
    )

    @http_get("/", response=List[model_config.retrieve_schema])
    def list_images(self, filters: ImageFilterSchema = Query(...)):
        user_id = self.context.request.user.id
        queryset = self.model_config.model.objects.filter(
            workspace__user_id=user_id
        ).select_related("workspace")
        return filters.filter(queryset)

    @http_get("/{uuid}/download")
    def download_image_file(self, request, uuid: UUID):
        image = self.get_object_or_exception(self.model_config.model, uuid=uuid)
        return FileResponse(
            image.image_file.open("rb"),
            as_attachment=True,
            filename=image.image_file.name,
        )


@api_controller(
    "/internal/images",
    auth=[ServiceHMACAuth()],
    tags=["image", "internal"],
)
class ImageControllerInternal(ModelControllerBase):
    service_type = ImageModelService
    model_config = ModelConfig(
        model=Image,
        retrieve_schema=ImageResponse,
        allowed_routes=["find_one", "delete"],
    )

    @http_get("/", response=List[model_config.retrieve_schema])
    def list_images(self, filters: ImageFilterSchema = Query(...)):
        return filters.filter(self.model_config.model.objects.all())
