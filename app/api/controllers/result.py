from typing import List
from ninja_extra import (
    ModelControllerBase,
    ModelConfig,
    api_controller,
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
