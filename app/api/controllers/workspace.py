from uuid import UUID
from typing import List
from ninja import Query, File, Header
from ninja.files import UploadedFile
from ninja_extra import (
    ModelControllerBase,
    ModelConfig,
    api_controller,
    http_get,
    http_post,
    http_patch,
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
from app.api.schemas.tus import TusBaseHeaders, TusPostHeaders, TusPatchHeaders
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

    def _get_tus_handler(self, request, uuid: UUID):
        workspace = self.get_object_or_exception(self.model_config.model, uuid=uuid)
        tus_view = WorkspaceTusUploadView()
        tus_view.request = request
        tus_view.workspace = workspace
        return tus_view

    @http_generic(
        "/{uuid}/upload-images-tus",
        methods=["OPTIONS"],
        summary="TUS Discovery",
        tags=["tus"],
    )
    def tus_options(self, request, uuid: UUID):
        return self._get_tus_handler(request, uuid).options(request)

    @http_post("/{uuid}/upload-images-tus", summary="TUS Create Upload", tags=["tus"])
    def tus_post(self, request, uuid: UUID, headers: TusPostHeaders = Header(...)):
        request.path += "/"  # used in location header by django-tus
        return self._get_tus_handler(request, uuid).post(request)

    @http_generic(
        "/{uuid}/upload-images-tus/{resource_id}",
        summary="TUS Resume Check",
        methods=["HEAD"],
        tags=["tus"],
    )
    def tus_head(
        self,
        request,
        uuid: UUID,
        resource_id: str,
        headers: TusBaseHeaders = Header(...),
    ):
        return self._get_tus_handler(request, uuid).head(request, resource_id)

    @http_patch(
        "/{uuid}/upload-images-tus/{resource_id}",
        summary="TUS Chunk Upload",
        tags=["tus"],
    )
    def tus_patch(
        self,
        request,
        uuid: UUID,
        resource_id: str,
        headers: TusPatchHeaders = Header(...),
    ):
        return self._get_tus_handler(request, uuid).patch(request, resource_id)

    @http_generic(
        "/{uuid}/upload-images-tus/{resource_id}",
        methods=["OPTIONS"],
        summary="TUS Resource Options",
        tags=["tus"],
    )
    def tus_resource_options(self, request, uuid: UUID, resource_id: str):
        return self._get_tus_handler(request, uuid).options(request)


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
