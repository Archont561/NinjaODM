from ninja_extra import NinjaExtraAPI

from app.api.controllers.token import InternalTokenController
from app.api.controllers.workspace import (
    WorkspaceControllerInternal,
    WorkspaceControllerPublic,
)


def create_api() -> NinjaExtraAPI:
    api = NinjaExtraAPI()
    api.register_controllers(
        InternalTokenController,
        WorkspaceControllerInternal,
        WorkspaceControllerPublic,
    )
    return api
