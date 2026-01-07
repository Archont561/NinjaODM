from ninja_extra import (
    ModelControllerBase,
    ModelConfig,
    api_controller,
)

from app.api.auth.service import ServiceHMACAuth
from app.api.auth.user import ServiceUserJWTAuth
from app.api.models.image import Image
from app.api.permissions.image import IsImageOwner
from app.api.schemas.image import ImageResponse
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
        allowed_routes=["find_one", "list", "delete"],
        pagination=None,
        list_route_info={
            "queryset_getter": lambda self,
            **kw: self.model_config.model.objects.filter(
                workspace__user_id=self.context.request.user.id
            ).select_related("workspace"),
        },
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
        allowed_routes=["find_one", "list", "delete"],
    )
