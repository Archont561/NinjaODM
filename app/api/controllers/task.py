from uuid import UUID
from typing import List, Literal
from ninja import Query, Body
from ninja_extra import (
    api_controller,
    ModelControllerBase,
    ModelConfig,
    http_post,
    http_get,
)
from app.api.constants.odm import NodeODMTaskStatus
from app.api.auth.service import ServiceHMACAuth
from app.api.auth.user import ServiceUserJWTAuth
from app.api.auth.nodeodm import NodeODMServiceAuth
from app.api.models.task import ODMTask
from app.api.models.workspace import Workspace
from app.api.permissions.task import IsTaskOwner, IsTaskStateTerminal, CanCreateTask
from app.api.permissions.core import IsAuthorizedService
from app.api.permissions.workspace import IsWorkspaceOwner
from app.api.schemas.task import (
    CreateTask,
    UpdateTask,
    ODMTaskWebhookInternal,
    TaskResponse,
    TaskFilterSchema,
)
from app.api.schemas.core import MessageSchema
from app.api.services.task import TaskModelService


@api_controller(
    "/tasks",
    auth=[ServiceUserJWTAuth(), ServiceHMACAuth()],
    permissions=[IsTaskOwner | IsAuthorizedService],
    tags=["task", "public"],
)
class TaskControllerPublic(ModelControllerBase):
    service_type = TaskModelService
    model_config = ModelConfig(
        model=ODMTask,
        create_schema=CreateTask,
        retrieve_schema=TaskResponse,
        update_schema=UpdateTask,
        allowed_routes=["find_one", "delete"],
        delete_route_info={
            "permissions": [(IsTaskOwner | IsAuthorizedService) & IsTaskStateTerminal],
            "operation_id": "deleteTask",
        },
        find_one_route_info={
            "operation_id": "getTask",
        },
    )

    @http_post(
        "/",
        response={201: model_config.retrieve_schema},
        operation_id="createTask",
        permissions=[(IsWorkspaceOwner | IsAuthorizedService) & CanCreateTask],
    )
    def create_task(self, data: model_config.create_schema = Body(...)):
        ws = self.get_object_or_exception(Workspace, uuid=data.workspace_uuid)
        self.check_object_permissions(ws)
        return 201, self.service.create(data, workspace=ws)

    @http_get(
        "/",
        response=List[model_config.retrieve_schema],
        operation_id="listTasks",
    )
    def list_tasks(self, filters: TaskFilterSchema = Query(...)):
        user_id = self.context.request.user.id
        queryset = self.model_config.model.objects.filter(
            workspace__user_id=user_id
        ).select_related("workspace")
        return filters.filter(queryset)

    @http_post(
        "/{uuid}/{action}",
        response=model_config.retrieve_schema,
        operation_id="callTaskAction",
    )
    def task_action(
        self, request, uuid: UUID, action: Literal["pause", "resume", "cancel"]
    ):
        task = self.get_object_or_exception(ODMTask, uuid=uuid)
        return self.service.action(action, task, self.model_config.update_schema())


@api_controller(
    "/internal/tasks",
    auth=[ServiceHMACAuth()],
    tags=["task", "internal"],
)
class TaskControllerInternal(ModelControllerBase):
    service_type = TaskModelService
    model_config = ModelConfig(
        model=ODMTask,
        retrieve_schema=TaskResponse,
        update_schema=UpdateTask,
        allowed_routes=[],
    )

    @http_get(
        "/",
        response=List[model_config.retrieve_schema],
        operation_id="listTasksInternal",
    )
    def list_tasks(self, filters: TaskFilterSchema = Query(...)):
        queryset = self.model_config.model.objects.all()
        return filters.filter(queryset)

    @http_post(
        "/{uuid}/webhooks/odm",
        response=MessageSchema,
        auth=NodeODMServiceAuth(),
        operation_id="callTaskOdmWebhook",
    )
    def nodeodm_webhook(
        self, request, uuid: UUID, signature: str, data: ODMTaskWebhookInternal
    ):
        task = self.get_object_or_exception(ODMTask, uuid=uuid)
        match data.status.code:
            case NodeODMTaskStatus.FAILED:
                self.service.handle_failure(task)
            case NodeODMTaskStatus.COMPLETED:
                self.service.proceed_next_task_step(
                    task, self.model_config.update_schema()
                )
            case _:  # QUEUED, CANCELED, RUNNING (server already handles that)
                pass
        return {"message": "ok"}
