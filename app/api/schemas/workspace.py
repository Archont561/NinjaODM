from uuid import UUID
from typing import Optional, Annotated
from ninja import ModelSchema, Schema, FilterSchema, FilterLookup
from datetime import datetime

from app.api.models.workspace import Workspace


class CreateWorkspace(Schema):
    name: Optional[str] = None


class CreateWorkspaceInternal(CreateWorkspace):
    user_id: str


class UpdateWorkspace(Schema):
    name: str


class WorkspaceResponse(ModelSchema):
    class Meta:
        model = Workspace
        fields = ["uuid", "name", "created_at"]


class WorkspaceResponseInternal(ModelSchema):
    class Meta:
        model = Workspace
        fields = ["user_id", "uuid", "name", "created_at"]


class WorkspaceFilterSchema(FilterSchema):
    name: Annotated[Optional[str], FilterLookup("name__icontains")] = None
    created_after: Annotated[Optional[datetime], FilterLookup("created_at__gte")] = None
    created_before: Annotated[Optional[datetime], FilterLookup("created_at__lte")] = (
        None
    )


class WorkspaceFilterSchemaInternal(WorkspaceFilterSchema):
    user_id: Annotated[Optional[str], FilterLookup("user_id__icontains")] = None


class WorkspaceBaseSSEData(Schema):
    uuid: UUID
    name: str


class WorkspaceCreatedSSEData(WorkspaceBaseSSEData): ...


class WorkspaceUpdatedSSEData(WorkspaceBaseSSEData): ...


class WorkspaceDeletedSSEData(WorkspaceBaseSSEData): ...


class WorkspaceImagesUploadedSSEData(Schema):
    uuid: UUID
    uploaded: int
