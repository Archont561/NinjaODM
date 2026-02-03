from ninja.errors import HttpError

from app.api.models.task import ODMTask
from app.api.models.workspace import Workspace
from .core import IsServiceUser, BaseObjectPermission


class IsTaskOwner(IsServiceUser):
    def has_object_permission(self, request, controller, obj: ODMTask):
        return obj.workspace.user_id == request.user.id


class CanCreateTask(BaseObjectPermission):
    def has_object_permission(self, request, controller, obj: Workspace):
        return obj.images.count() > 0


class IsTaskStateTerminal(BaseObjectPermission):
    def has_object_permission(self, request, controller, obj: ODMTask):
        if not obj.odm_status.is_terminal():
            raise HttpError(409, "Task cannot be deleted while it is running")
        return True
