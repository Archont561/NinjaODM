from app.api.models.gcp import GroundControlPoint
from .core import IsServiceUser


class IsGCPOwner(IsServiceUser):
    def has_object_permission(self, request, controller, obj: GroundControlPoint):
        return obj.image.workspace.user_id == request.user.id
