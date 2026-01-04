from ninja_extra import permissions

from app.api.models.image import Image


class IsImageOwner(permissions.BasePermission):
    def has_permission(self, request, controller):
        return True

    def has_object_permission(self, request, controller, obj: Image):
        return obj.workspace.user_id == request.user.id
