from typing import List
from ninja import Query
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
from app.api.schemas.gcp import (
    GCPCreate,
    GCPUpdate,
    GCPResponse,
    GCPFeatureCollection,
    GCPFilterSchema,
)
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
        allowed_routes=["find_one", "patch", "delete", "create"],
        create_route_info={
            "path": "/?image_uuid=uuid",
            "permissions": [CanCreateGCP],
            "custom_handler": lambda self, data, **kw: self.service.create(
                data, **self.context.kwargs, **kw
            ),
            'operation_id': 'createGCP',
        },
        find_one_route_info={
            'operation_id': 'getGCP',
        },
        patch_route_info={
            'operation_id': 'updateGCP',
        },
        delete_route_info={
            'operation_id': 'deleteGCP',
        },
    )

    def get_queryset(self):
        user_id = self.context.request.user.id
        return self.model_config.model.objects.filter(image__workspace__user_id=user_id)

    @http_get(
        "/", 
        response=List[model_config.retrieve_schema],
        operation_id='listGCPs',
    )
    def list_gcps(self, filters: GCPFilterSchema = Query(...)):
        return filters.filter(self.get_queryset())

    @http_get(
        "/geojson", 
        response=GCPFeatureCollection, 
        tags=["gcp", "public", "geojson"],
        operation_id='listGCPsAsGeojson',
    )
    def list_gcps_as_geojson(self, filters: GCPFilterSchema = Query(...)):
        return self.service.queryset_to_geojson(filters.filter(self.get_queryset()))


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
        allowed_routes=["find_one", "patch", "delete", "create"],
        create_route_info={
            "path": "/?image_uuid=uuid",
            "permissions": [CanCreateGCP],
            "custom_handler": lambda self, data, **kw: self.service.create(
                data, **self.context.kwargs, **kw
            ),
            'operation_id': 'createGCPInternal',
        },
        find_one_route_info={
            'operation_id': 'getGCPInternal',
        },
        patch_route_info={
            'operation_id': 'updateGCPInternal',
        },
        delete_route_info={
            'operation_id': 'deleteGCPInternal',
        },
    )

    @http_get(
        "/", 
        response=List[model_config.retrieve_schema],
        operation_id='listGCPsInternal',
    )
    def list_gcps(self, filters: GCPFilterSchema = Query(...)):
        queryset = self.model_config.model.objects.all()
        return filters.filter(queryset)
