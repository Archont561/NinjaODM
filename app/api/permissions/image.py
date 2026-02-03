from app.api.models.image import Image
from .core import IsServiceUser


class IsImageOwner(IsServiceUser):
    def has_object_permission(self, request, controller, obj: Image):
        return obj.workspace.user_id == request.user.id
