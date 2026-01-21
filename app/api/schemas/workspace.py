from uuid import UUID
from typing import Optional, Annotated
from ninja import ModelSchema, Schema, FilterSchema, FilterLookup
from datetime import datetime

from app.api.models.workspace import Workspace


class CreateWorkspaceInternal(Schema):
    user_id: str
    name: Optional[str] = None


class CreateWorkspacePublic(Schema):
    name: Optional[str] = None


class UpdateWorkspaceInternal(Schema):
    user_id: Optional[str] = None
    name: Optional[str] = None


class UpdateWorkspacePublic(Schema):
    name: str


class WorkspaceResponseInternal(ModelSchema):
    class Meta:
        model = Workspace
        fields = ["user_id", "uuid", "name", "created_at"]


class WorkspaceResponsePublic(ModelSchema):
    class Meta:
        model = Workspace
        fields = ["uuid", "name", "created_at"]


class WorkspaceFilterSchemaPublic(FilterSchema):
    name: Annotated[Optional[str], FilterLookup("name__icontains")] = None
    created_after: Annotated[Optional[datetime], FilterLookup("created_at__gte")] = None
    created_before: Annotated[Optional[datetime], FilterLookup("created_at__lte")] = (
        None
    )


class WorkspaceFilterSchemaInternal(WorkspaceFilterSchemaPublic):
    user_id: Annotated[Optional[str], FilterLookup("user_id__icontains")] = None


class WorkspaceBaseSSEData(Schema):
    uuid: UUID
    name: str


class WorkspaceCreatedSSEData(WorkspaceBaseSSEData):
    ...


class WorkspaceUpdatedSSEData(WorkspaceBaseSSEData):
    ...


class WorkspaceDeletedSSEData(WorkspaceBaseSSEData):
    ...


class WorkspaceImagesUploadedSSEData(Schema):
    uuid: UUID
    uploaded: int
