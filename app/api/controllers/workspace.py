from typing import List
from ninja_extra import (
    ModelEndpointFactory,
    ModelControllerBase,
    ModelConfig,
    api_controller,
    http_get,
    http_post,
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
)
from app.api.services.workspace import WorkspaceModelService


@api_controller(
    "/workspaces",
    auth=[ServiceUserJWTAuth()],
    permissions=[IsWorkspaceOwner()],
    tags=["workspace", "public"],
)
class WorkspaceControllerPublic(ModelControllerBase):
    """Public API - users can only access their own workspaces"""
    
    service_type = WorkspaceModelService
    model_config = ModelConfig(
        model=Workspace,
        create_schema=CreateWorkspacePublic,
        retrieve_schema=WorkspaceResponsePublic,
        update_schema=UpdateWorkspacePublic,
        allowed_routes=["find_one", "patch", "delete"],
    )

    @http_get("/", response=List[model_config.retrieve_schema])
    def list_my_workspaces(self, request):
        return Workspace.objects.filter(user_id=request.user.id)

    @http_post("/", response={201: model_config.retrieve_schema})
    def create_workspace(self, request, payload: model_config.create_schema):
        """Create workspace and auto-assign to current user"""
        return 201, self.service.create(
            payload,
            user_id=request.user.id
        )


@api_controller(
    "/internal/workspaces",
    auth=[ServiceHMACAuth()],
    tags=["workspace", "internal"],
)
class WorkspaceControllerInternal(ModelControllerBase):
    service_type = WorkspaceModelService
    model_config = ModelConfig(
        model=Workspace,
        create_schema=CreateWorkspaceInternal,
        retrieve_schema=WorkspaceResponseInternal,
        update_schema=UpdateWorkspaceInternal,
    )
