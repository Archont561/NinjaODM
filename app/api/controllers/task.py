from uuid import UUID
from typing import List
from ninja import Query
from ninja_extra import (
    api_controller,
    ModelControllerBase,
    ModelConfig,
    http_post,
    http_get,
)

from app.api.auth.service import ServiceHMACAuth
from app.api.auth.user import ServiceUserJWTAuth
from app.api.models.task import ODMTask
from app.api.permissions.task import IsTaskOwner, IsTaskStateTerminal, CanCreateTask
from app.api.schemas.task import (
    CreateTaskInternal,
    CreateTaskPublic,
    TaskResponse,
    TaskFilterSchema,
)
from app.api.services.task import TaskModelService


@api_controller(
    "/tasks",
    auth=[ServiceUserJWTAuth()],
    permissions=[IsTaskOwner],
    tags=["task", "public"],
)
class TaskControllerPublic(ModelControllerBase):
    service_type = TaskModelService
    model_config = ModelConfig(
        model=ODMTask,
        create_schema=CreateTaskPublic,
        retrieve_schema=TaskResponse,
        allowed_routes=["find_one", "create", "delete"],
        delete_route_info={
            "permissions": [IsTaskOwner & IsTaskStateTerminal],
        },
        create_route_info={
            "path": "/?workspace_uuid=uuid",
            "permissions": [CanCreateTask],
            "custom_handler": lambda self, data, **kw: self.service.create(
                data, **self.context.kwargs, **kw
            ),
        },
    )

    @http_get("/", response=List[model_config.retrieve_schema])
    def list_tasks(self, filters: TaskFilterSchema = Query(...)):
        user_id = self.context.request.user.id
        queryset = self.model_config.model.objects.filter(
            workspace__user_id=user_id
        ).select_related("workspace")
        return filters.filter(queryset)

    @http_post("/{uuid:task_uuid}/pause/", response=model_config.retrieve_schema)
    def pause_task(self, request, task_uuid: UUID):
        task = self.get_object_or_exception(ODMTask, uuid=task_uuid)
        self.service.pause(task)
        return task

    @http_post("/{uuid:task_uuid}/resume/", response=model_config.retrieve_schema)
    def resume_task(self, request, task_uuid: UUID):
        task = self.get_object_or_exception(ODMTask, uuid=task_uuid)
        self.service.resume(task)
        return task

    @http_post("/{uuid:task_uuid}/cancel/", response=model_config.retrieve_schema)
    def cancel_task(self, request, task_uuid: UUID):
        task = self.get_object_or_exception(ODMTask, uuid=task_uuid)
        self.service.cancel(task)
        return task


@api_controller(
    "/internal/tasks",
    auth=[ServiceHMACAuth()],
    tags=["task", "internal"],
)
class TaskControllerInternal(ModelControllerBase):
    service_type = TaskModelService
    model_config = ModelConfig(
        model=ODMTask,
        create_schema=CreateTaskInternal,
        retrieve_schema=TaskResponse,
        allowed_routes=["find_one", "create", "delete"],
        delete_route_info={
            "permissions": [IsTaskStateTerminal],
        },
        create_route_info={
            "path": "/?workspace_uuid=uuid",
            "permissions": [CanCreateTask],
            "custom_handler": lambda self, data, **kw: self.service.create(
                data, **self.context.kwargs, **kw
            ),
        },
    )

    @http_get("/", response=List[model_config.retrieve_schema])
    def list_tasks(self, filters: TaskFilterSchema = Query(...)):
        queryset = self.model_config.model.objects.all()
        return filters.filter(queryset)

    @http_post("/{uuid:task_uuid}/pause/", response=model_config.retrieve_schema)
    def pause_task(self, request, task_uuid: UUID):
        task = self.get_object_or_exception(ODMTask, uuid=task_uuid)
        self.service.pause(task)
        return task

    @http_post("/{uuid:task_uuid}/resume/", response=model_config.retrieve_schema)
    def resume_task(self, request, task_uuid: UUID):
        task = self.get_object_or_exception(ODMTask, uuid=task_uuid)
        self.service.resume(task)
        return task

    @http_post("/{uuid:task_uuid}/cancel/", response=model_config.retrieve_schema)
    def cancel_task(self, request, task_uuid: UUID):
        task = self.get_object_or_exception(ODMTask, uuid=task_uuid)
        self.service.cancel(task)
        return task
