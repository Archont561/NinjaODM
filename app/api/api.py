from ninja_extra import NinjaExtraAPI

from app.api.controllers.token import TokenControllerInternal
from app.api.controllers.workspace import (
    WorkspaceControllerInternal,
    WorkspaceControllerPublic,
)
from app.api.controllers.task import TaskControllerInternal, TaskControllerPublic


def create_api() -> NinjaExtraAPI:
    api = NinjaExtraAPI()
    api.register_controllers(
        TokenControllerInternal,
        WorkspaceControllerInternal,
        WorkspaceControllerPublic,
        TaskControllerInternal,
        TaskControllerPublic,
    )
    return api
