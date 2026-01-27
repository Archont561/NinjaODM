from django.db.models import Q
from ninja_extra import permissions

from app.api.models.workspace import Workspace
from app.api.models.task import ODMTask
from app.api.constants.odm import ODMTaskStatus


class IsWorkspaceOwner(permissions.BasePermission):
    def has_permission(self, request, controller):
        return True

    def has_object_permission(self, request, controller, obj: Workspace):
        return obj.user_id == request.user.id


class CanDeleteWorkspace(permissions.BasePermission):
    def has_permission(self, request, controller):
        return True

    def has_object_permission(self, request, controller, obj: Workspace):
        can_delete = not ODMTask.objects.filter(
            Q(workspace=obj) & ~Q(status__in=ODMTaskStatus.terminal_states())
        ).exists()
        return can_delete
