from uuid import UUID
from typing import Optional
from pydantic import Field
from ninja import ModelSchema, Schema

from app.api.models.task import ODMTask
from app.api.schemas.odm_option import ODMOptionsInternal, ODMOptionsPublic


class CreateTaskInternal(Schema):
    options: ODMOptionsInternal


class CreateTaskPublic(Schema):
    options: ODMOptionsPublic


class TaskResponse(ModelSchema):
    workspace_uuid: UUID

    class Meta:
        model = ODMTask
        fields = [
            "uuid",
            "status",
            "step",
            "options",
            "created_at",
        ]


    @staticmethod
    def resolve_workspace_uuid(obj: ODMTask):
        return obj.workspace.uuid
