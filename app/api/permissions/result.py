from ninja_extra import permissions

from app.api.models.result import ODMTaskResult


class IsResultOwner(permissions.BasePermission):
    def has_permission(self, request, controller):
        return True

    def has_object_permission(self, request, controller, obj: ODMTaskResult):
        return obj.workspace.user_id == request.user.id


class IsRefererResultOwner(permissions.BasePermission):
    def has_permission(self, request, controller):
        return request.referer.id is not None

    def has_object_permission(self, request, controller, obj: ODMTaskResult):
        return (
            obj.workspace.user_id == request.referer.id
            and obj.uuid == request.referer.result_uuid
        )
