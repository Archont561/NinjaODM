from ninja_extra import permissions
from ninja.errors import HttpError
from django.http import HttpRequest

from app.api.models.task import ODMTask
from app.api.models.workspace import Workspace


class CanCreateTask(permissions.BasePermission):
    def has_permission(self, request: HttpRequest, controller):
        workspace_uuid = request.GET.get("workspace_uuid")
        try:
            workspace = Workspace.objects.get(uuid=workspace_uuid)
        except Workspace.DoesNotExist:
            return False

        controller.context.kwargs["workspace"] = workspace

        is_service = bool(getattr(request, "service", None))
        is_owner = workspace.user_id == request.user.id

        return is_service or is_owner


class IsTaskOwner(permissions.BasePermission):
    def has_permission(self, request, controller):
        return True

    def has_object_permission(self, request, controller, obj: ODMTask):
        return obj.workspace.user_id == request.user.id


class IsTaskStateTerminal(permissions.BasePermission):
    def has_permission(self, request, controller):
        return True

    def has_object_permission(self, request, controller, obj: ODMTask):
        if not obj.odm_status.is_terminal():
            raise HttpError(400, "Task must be in a terminal state for this action")
        return True
