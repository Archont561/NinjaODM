from ninja_extra import permissions
from django.http import HttpRequest

from app.api.models.gcp import GroundControlPoint
from app.api.models.image import Image


class CanCreateGCP(permissions.BasePermission):
    def has_permission(self, request: HttpRequest, controller):
        image_uuid = request.GET.get('image_uuid')
        try:
            image = Image.objects.get(uuid=image_uuid)
        except Image.DoesNotExist:
            return False

        controller.context.kwargs["image"] = image

        is_service = bool(getattr(request, "service", None))
        is_owner = image.workspace.user_id == request.user.id

        return is_service or is_owner


class IsGCPOwner(permissions.BasePermission):
    def has_permission(self, request, controller):
        return True

    def has_object_permission(self, request, controller, obj: GroundControlPoint):
        return obj.image.workspace.user_id == request.user.id
