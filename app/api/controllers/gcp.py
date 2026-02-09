from typing import List
from ninja import Query, Body
from ninja_extra import (
    ModelControllerBase,
    ModelConfig,
    api_controller,
    http_get,
    http_post,
    http_patch,
    http_delete,
)

from app.api.auth.service import ServiceHMACAuth
from app.api.auth.user import ServiceUserJWTAuth
from app.api.models.gcp import GroundControlPoint
from app.api.models.image import Image
from app.api.permissions.gcp import IsGCPOwner
from app.api.permissions.core import IsAuthorizedService
from app.api.permissions.image import IsImageOwner
from app.api.schemas.gcp import (
    GCPCreate,
    GCPUpdate,
    GCPBulkCreate,
    GCPBulkUpdate,
    GCPBulkDelete,
    GCPResponse,
    GCPFeatureCollection,
    GCPFilterSchema,
    GCPFilterSchemaInternal,
)
from app.api.services.gcp import GCPModelService


@api_controller(
    "/gcps",
    auth=[ServiceUserJWTAuth(), ServiceHMACAuth()],
    permissions=[IsGCPOwner | IsAuthorizedService],
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
        allowed_routes=["find_one", "patch", "delete"],
        find_one_route_info={
            "operation_id": "getGCP",
        },
        patch_route_info={
            "operation_id": "updateGCP",
        },
        delete_route_info={
            "operation_id": "deleteGCP",
        },
    )

    @http_post(
        "/",
        response={201: model_config.retrieve_schema},
        operation_id="createGCP",
        permissions=[IsImageOwner | IsAuthorizedService],
    )
    def create_gcp(self, data: model_config.create_schema = Body(...)):
        image = self.get_object_or_exception(Image, uuid=data.image_uuid)
        self.check_object_permissions(image)
        return 201, self.service.create(data, image=image)

    def _get_queryset(self):
        user_id = self.context.request.user.id
        return self.model_config.model.objects.filter(
            image__workspace__user_id=user_id
        ).select_related("image", "image__workspace")

    @http_get(
        "/",
        response=List[model_config.retrieve_schema],
        operation_id="listGCPs",
    )
    def list_gcps(self, filters: GCPFilterSchema = Query(...)):
        return filters.filter(self._get_queryset())

    @http_get(
        "/geojson",
        response=GCPFeatureCollection,
        tags=["gcp", "public", "geojson"],
        operation_id="listGCPsAsGeojson",
    )
    def list_gcps_as_geojson(self, filters: GCPFilterSchema = Query(...)):
        return self.service.queryset_to_geojson(filters.filter(self._get_queryset()))

    @http_post(
        "/bulk",
        response={201: List[model_config.retrieve_schema]},
        operation_id="bulkCreateGCPs",
        permissions=[IsImageOwner | IsAuthorizedService],
    )
    def bulk_create_gcps(self, payload: GCPBulkCreate = Body(...)):
        uuids = { item.image_uuid for item in payload }

        for uuid in uuids:
            image = self.get_object_or_exception(Image, uuid=uuid)
            self.check_object_permissions(image)

        created = self.service.bulk_create(payload)
        return 201, created

    @http_patch(
        "/bulk",
        response=List[model_config.retrieve_schema],
        operation_id="bulkUpdateGCPs",
    )
    def bulk_update_gcps(self, payload: GCPBulkUpdate):
        uuids = [item.uuid for item in payload]

        for uuid in uuids:
            gcp = self.get_object_or_exception(self.model, uuid=uuid)
            self.check_object_permissions(gcp)

        return self.service.bulk_update(payload)
    
    @http_delete(
        "/bulk",
        response={204: None},
        operation_id="bulkDeleteGCPs",
    )
    def bulk_delete_gcps(self, uuids: GCPBulkDelete = Body(...)):
        for uuid in uuids:
            gcp = self.get_object_or_exception(self.model, uuid=uuid)
            self.check_object_permissions(gcp)

        self.service.bulk_delete(uuids)
        return 204, None


@api_controller(
    "/internal/gcps",
    auth=[ServiceHMACAuth()],
    tags=["gcp", "internal"],
)
class GCPControllerInternal(ModelControllerBase):
    service_type = GCPModelService
    model_config = ModelConfig(
        model=GroundControlPoint,
        retrieve_schema=GCPResponse,
        allowed_routes=[],
    )

    @http_get(
        "/",
        response=List[model_config.retrieve_schema],
        operation_id="listGCPsInternal",
    )
    def list_gcps(self, filters: GCPFilterSchemaInternal = Query(...)):
        queryset = self.model_config.model.objects.all().select_related(
            "image", "image__workspace"
        )
        return filters.filter(queryset)
