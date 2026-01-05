from typing import Optional
from ninja import ModelSchema, Schema, FilterSchema
from pydantic import Field
from datetime import datetime

from app.api.models.workspace import Workspace


class CreateWorkspaceInternal(Schema):
    user_id: int
    name: Optional[str] = None


class CreateWorkspacePublic(Schema):
    name: Optional[str] = None


class UpdateWorkspaceInternal(Schema):
    user_id: Optional[int] = None
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


class WorkspaceFilterSchema(FilterSchema):
    name: Optional[str] = Field(None, q="name__icontains")
    created_after: Optional[datetime] = Field(None, q="created_at__gte")
    created_before: Optional[datetime] = Field(None, q="created_at__lte")
