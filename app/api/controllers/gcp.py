from ninja_extra import (
    ModelControllerBase,
    ModelConfig,
    api_controller,
    http_get,
)

from app.api.auth.service import ServiceHMACAuth
from app.api.auth.user import ServiceUserJWTAuth
from app.api.models.gcp import GroundControlPoint
from app.api.permissions.gcp import IsGCPOwner, CanCreateGCP
from app.api.schemas.gcp import GCPCreate, GCPUpdate, GCPResponse, GCPFeatureCollection
from app.api.services.gcp import GCPModelService


@api_controller(
    "/gcps",
    auth=[ServiceUserJWTAuth()],
    permissions=[IsGCPOwner],
    tags=["gcp", "public"],
)
class GCPControllerPublic(ModelControllerBase):
    service_type = GCPModelService
    model_config = ModelConfig(
        model=GroundControlPoint,
        create_schema=GCPCreate,
        patch_schema=GCPUpdate,
        update_schema=GCPUpdate,
        retrieve_schema=GCPResponse,
        pagination=None,
        list_route_info={
            "queryset_getter": lambda self, **kw: self.get_queryset(**kw),
        },
        create_route_info={
            "path": "/?image_uuid=uuid",
            "permissions": [CanCreateGCP],
            "custom_handler": lambda self, data, **kw: self.service.create(data, **self.context.kwargs, **kw)
        },
    )

    def get_queryset(self, **kwargs):
        return self.model_config.model.objects.filter(
            image__workspace__user_id=self.context.request.user.id
        )

    @http_get("/geojson", response=GCPFeatureCollection, tags=["gcp", "public", "geojson"])
    def list_as_geojson(self, request, **kwargs):
        result =  self.service.queryset_to_geojson(self.get_queryset())
        return result


@api_controller(
    "/internal/gcps",
    auth=[ServiceHMACAuth()],
    tags=["gcp", "internal"],
)
class GCPControllerInternal(ModelControllerBase):
    service_type = GCPModelService
    model_config = ModelConfig(
        model=GroundControlPoint,
        create_schema=GCPCreate,
        update_schema=GCPUpdate,
        patch_schema=GCPUpdate,
        retrieve_schema=GCPResponse,
        pagination=None,
        create_route_info={
            "path": "/?image_uuid=uuid",
            "permissions": [CanCreateGCP],
            "custom_handler": lambda self, data, **kw: self.service.create(data, **self.context.kwargs, **kw)
        },
    )
