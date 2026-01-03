from django.http import HttpRequest

from ninja_extra import permissions

from app.api.constants.user import ServiceUser
from app.api.models.workspace import Workspace


class IsWorkspaceOwner(permissions.BasePermission):
    def has_permission(self, request, controller):
        return isinstance(getattr(request, "user"), ServiceUser)

    def has_object_permission(self, request: HttpRequest, controller, obj: Workspace):
        return obj.user_id == request.user.id
