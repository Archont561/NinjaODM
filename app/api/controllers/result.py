from uuid import UUID
from typing import List
from django.http import FileResponse
from ninja_extra import (
    ModelControllerBase,
    ModelConfig,
    api_controller,
    http_get,
)

from app.api.auth.service import ServiceHMACAuth
from app.api.auth.user import ServiceUserJWTAuth
from app.api.models.result import ODMTaskResult
from app.api.permissions.result import IsResultOwner
from app.api.schemas.result import ResultResponse
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
        allowed_routes=["find_one", "list", "delete"],
        pagination=None,
        list_route_info={
            "queryset_getter": lambda self, **kw: self.model_config.model.objects.filter(
                workspace__user_id=self.context.request.user.id
            ).select_related("workspace"),
        },
    )

    @http_get("/download/{uuid}")
    def download_result_file(self, request, uuid: UUID):
        result = self.get_object_or_exception(self.model_config.model, uuid=uuid)
        return FileResponse(
            result.file.open("rb"),
            as_attachment=True,
            filename=result.file.name
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
        allowed_routes=["find_one", "list", "delete"],
    )
