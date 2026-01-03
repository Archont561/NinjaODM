from ninja_extra import permissions

from app.api.models.workspace import Workspace


class IsWorkspaceOwner(permissions.BasePermission):
    def has_permission(self, request, controller):
        return True

    def has_object_permission(self, request, controller, obj: Workspace):
        return obj.user_id == request.user.id
