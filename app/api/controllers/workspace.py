from uuid import UUID
from typing import List
from ninja import Query, File
from ninja.files import UploadedFile
from ninja_extra import (
    ModelControllerBase,
    ModelConfig,
    api_controller,
    http_get,
    http_post,
    http_generic,
)
from django_tus.views import TusUpload
from django_tus.signals import tus_upload_finished_signal

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
    WorkspaceFilterSchemaPublic,
    WorkspaceFilterSchemaInternal,
)
from app.api.schemas.image import ImageResponse
from app.api.services.workspace import WorkspaceModelService


class WorkspaceTusUploadView(TusUpload):
    def send_signal(self, tus_file):
        tus_upload_finished_signal.send(
            sender=self.workspace.__class__, tus_file=tus_file, workspace=self.workspace
        )


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
            "custom_handler": lambda self, data, **kw: self.service.create(
                data, user_id=self.context.request.user.id, **kw
            ),
        },
    )

    @http_get("/", response=List[model_config.retrieve_schema])
    def list_workspaces(self, filters: WorkspaceFilterSchemaPublic = Query(...)):
        user_id = self.context.request.user.id
        queryset = self.model_config.model.objects.filter(user_id=user_id)
        return filters.filter(queryset)

    @http_post("/{uuid}/upload-image", response=ImageResponse)
    def upload_file(self, request, uuid: UUID, image_file: File[UploadedFile]):
        workspace = self.get_object_or_exception(self.model_config.model, uuid=uuid)
        image = self.service.save_images(workspace, [image_file])[0]
        return image

    @http_post("/{uuid}/upload-images", response=List[ImageResponse])
    def upload_files(self, request, uuid: UUID, image_files: File[List[UploadedFile]]):
        workspace = self.get_object_or_exception(self.model_config.model, uuid=uuid)
        images = self.service.save_images(workspace, image_files)
        return images

    def _run_tus_logic(self, request, uuid, resource_id=None):
        workspace = self.get_object_or_exception(self.model_config.model, uuid=uuid)

        tus_view = WorkspaceTusUploadView()
        tus_view.request = request
        tus_view.workspace = workspace

        method_map = {
            "POST": tus_view.post,
            "PATCH": lambda r: tus_view.patch(r, resource_id),
            "HEAD": lambda r: tus_view.head(r, resource_id),
            "OPTIONS": tus_view.options,
        }

        handler = method_map.get(request.method.upper())
        return handler(request)

    @http_generic("/{uuid}/upload-images-tus/", methods=["post", "options"])
    def tus_upload(self, request, uuid: UUID):
        return self._run_tus_logic(request, uuid)

    @http_generic(
        "/{uuid}/upload-images-tus/{resource_id}", methods=["patch", "head", "options"]
    )
    def tus_upload_with_resource(self, request, uuid: UUID, resource_id: UUID):
        return self._run_tus_logic(request, uuid, resource_id)


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
        allowed_routes=["create", "find_one", "update", "patch", "delete"],
    )

    @http_get("/", response=List[model_config.retrieve_schema])
    def list_workspaces(self, filters: WorkspaceFilterSchemaInternal = Query(...)):
        return filters.filter(self.model_config.model.objects.all())
