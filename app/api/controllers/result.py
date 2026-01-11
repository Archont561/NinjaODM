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
from app.api.auth.share import ShareResultsApiKeyAuth
from app.api.constants.token import ShareToken
from app.api.models.result import ODMTaskResult
from app.api.permissions.result import IsResultOwner, IsRefererResultOwner
from app.api.schemas.result import ResultResponse, ResultFilterSchema
from app.api.services.result import ResultModelService


@api_controller(
    "/results",
    auth=[ServiceUserJWTAuth()],
    permissions=[IsResultOwner],
    tags=["result", "public"],
)
class ResultControllerPublic(ModelControllerBase):
    service_type = ResultModelService
    model_config = ModelConfig(
        model=ODMTaskResult,
        retrieve_schema=ResultResponse,
        allowed_routes=["find_one", "delete"],
    )

    @http_get("/", response=List[model_config.retrieve_schema])
    def list_results(self, filters: ResultFilterSchema = Query(...)):
        user_id = self.context.request.user.id
        queryset = self.model_config.model.objects.filter(
            workspace__user_id=user_id
        ).select_related("workspace")
        return filters.filter(queryset)

    @http_get("/{uuid}/download")
    def download_result_file(self, request, uuid: UUID):
        result = self.get_object_or_exception(self.model_config.model, uuid=uuid)
        return FileResponse(
            result.file.open("rb"), as_attachment=True, filename=result.file.name
        )

    @http_get("/{uuid}/share")
    def get_share_api_key(self, request, uuid: UUID):
        result = self.get_object_or_exception(self.model_config.model, uuid=uuid)
        return {"share_api_key": ShareToken.for_result(result)}

    @http_get(
        "/{uuid}/shared",
        auth=ShareResultsApiKeyAuth(),
        permissions=[IsRefererResultOwner],
    )
    def download_shared_result_file(self, request, uuid: UUID, api_key: str):
        result = self.get_object_or_exception(self.model_config.model, uuid=uuid)
        return FileResponse(
            result.file.open("rb"), as_attachment=True, filename=result.file.name
        )


@api_controller(
    "/internal/results",
    auth=[ServiceHMACAuth()],
    tags=["result", "internal"],
)
class ResultControllerInternal(ModelControllerBase):
    service_type = ResultModelService
    model_config = ModelConfig(
        model=ODMTaskResult,
        retrieve_schema=ResultResponse,
        allowed_routes=["find_one", "delete"],
    )

    @http_get("/", response=List[model_config.retrieve_schema])
    def list_results(self, filters: ResultFilterSchema = Query(...)):
        return filters.filter(self.model_config.model.objects.all())
