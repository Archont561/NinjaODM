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
from app.api.models.workspace import Workspace
from app.api.permissions.workspace import IsWorkspaceOwner
from app.api.schemas.workspace import (
    CreateWorkspaceInternal,
    CreateWorkspacePublic,
    UpdateWorkspaceInternal,
    UpdateWorkspacePublic,
    WorkspaceResponseInternal,
    WorkspaceResponsePublic,
    WorkspaceFilterSchema,
)
from app.api.services.workspace import WorkspaceModelService


@api_controller(
    "/workspaces",
    auth=[ServiceUserJWTAuth()],
    permissions=[IsWorkspaceOwner],
    tags=["workspace", "public"],
)
class WorkspaceControllerPublic(ModelControllerBase):
    service_type = WorkspaceModelService
    model_config = ModelConfig(
        model=Workspace,
        create_schema=CreateWorkspacePublic,
        retrieve_schema=WorkspaceResponsePublic,
        update_schema=UpdateWorkspacePublic,
        allowed_routes=["find_one", "patch", "delete", "create"],
        create_route_info={
            "custom_handler": lambda self, data, **kw: self.service.create(data, user_id=self.context.request.user.id, **kw),
        },
    )

    @http_get("/", response=List[model_config.retrieve_schema])
    def list_workspaces(self, filters: WorkspaceFilterSchema = Query(...)):
        user_id = self.context.request.user.id
        queryset = self.model_config.model.objects.filter(user_id=user_id)
        return filters.filter(queryset)


@api_controller(
    "/internal/workspaces",
    auth=[ServiceHMACAuth()],
    tags=["workspace", "internal"],
)
class WorkspaceControllerInternal(ModelControllerBase):
    service_type = WorkspaceModelService
    model_config = ModelConfig(
        model=Workspace,
        list_filter_schema=WorkspaceFilterSchema,
        create_schema=CreateWorkspaceInternal,
        retrieve_schema=WorkspaceResponseInternal,
        update_schema=UpdateWorkspaceInternal,
        allowed_routes=["create", "find_one", "update", "patch", "delete"],
    )

    @http_get("/", response=List[model_config.retrieve_schema])
    def list_workspaces(self, filters: WorkspaceFilterSchema = Query(...)):
        return filters.filter(self.model_config.model.objects.all())
    