from injector import inject
from ninja import Body
from ninja_extra import (
    ControllerBase,
    api_controller,
    http_delete,
    http_get,
    http_patch,
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
from app.api.services.workspace import WorkspaceService


@api_controller(
    "/workspaces",
    auth=[ServiceUserJWTAuth()],
    tags=["workspace", "public"],
)
class WorkspaceControllerPublic(ControllerBase):
    @inject
    def __init__(self, workspace_service: WorkspaceService):
        self.workspace_service = workspace_service

    @http_get(
        "/",
        response=list[WorkspaceResponsePublic],
    )
    def list_workspaces(self, request):
        return self.workspace_service.list_for_user(request.user.id)

    @http_post(
        "/",
        response=WorkspaceResponsePublic,
    )
    def create_workspace(self, request, payload: CreateWorkspacePublic = Body(...)):
        return self.workspace_service.create_workspace(
            {"user_id": request.user.id, **payload.dict(exclude_unset=True)}
        )

    @http_get(
        "/{uuid}",
        response=WorkspaceResponsePublic,
        permissions=[IsWorkspaceOwner()],
    )
    def get_workspace(self, request, uuid: str):
        return self.get_object_or_exception(Workspace, uuid=uuid)

    @http_patch(
        "/{uuid}",
        response=WorkspaceResponsePublic,
        permissions=[IsWorkspaceOwner()],
    )
    def update_workspace(
        self,
        request,
        uuid: str,
        payload: UpdateWorkspacePublic = Body(...),
    ):
        workspace = self.get_object_or_exception(Workspace, uuid=uuid)
        return self.workspace_service.update_workspace(
            workspace, payload.dict(exclude_unset=True)
        )

    @http_delete(
        "/{uuid}",
        response={204: None},
        permissions=[IsWorkspaceOwner()],
    )
    def delete_workspace(self, request, uuid: str):
        workspace = self.get_object_or_exception(Workspace, uuid=uuid)
        self.workspace_service.delete_workspace(workspace)
        return 204, None


@api_controller(
    "/internal/workspaces",
    auth=[ServiceHMACAuth()],
    tags=["workspace", "internal"],
)
class WorkspaceControllerInternal:
    @inject
    def __init__(self, workspace_service: WorkspaceService):
        self.workspace_service = workspace_service

    @http_get(
        "/",
        response=list[WorkspaceResponseInternal],
    )
    def list_workspaces(self, request):
        return self.workspace_service.list_all()

    @http_post(
        "/",
        response=WorkspaceResponseInternal,
    )
    def create_workspace(self, request, payload: CreateWorkspaceInternal = Body(...)):
        return self.workspace_service.create_workspace(payload.dict(exclude_unset=True))

    @http_get(
        "/{uuid}",
        response=WorkspaceResponseInternal,
    )
    def get_workspace(self, request, uuid: str):
        return self.get_object_or_exception(Workspace, uuid=uuid)

    @http_patch(
        "/{uuid}",
        response=WorkspaceResponseInternal,
    )
    def update_workspace(
        self,
        request,
        uuid: str,
        payload: UpdateWorkspaceInternal = Body(...),
    ):
        workspace = self.get_object_or_exception(Workspace, uuid=uuid)
        return self.workspace_service.update_workspace(
            workspace, payload.dict(exclude_unset=True)
        )

    @http_delete(
        "/{uuid}",
        response={204: None},
    )
    def delete_workspace(self, request, uuid: str):
        workspace = self.get_object_or_exception(Workspace, uuid=uuid)
        self.workspace_service.delete_workspace(workspace)
        return 204, None
