from app.api.models.result import ODMTaskResult
from .core import IsServiceUser, IsReferrer


class IsResultOwner(IsServiceUser):
    def has_object_permission(self, request, controller, obj: ODMTaskResult):
        return obj.workspace.user_id == request.user.id


class DidReferrerGrantAccess(IsReferrer):
    def has_object_permission(self, request, controller, obj: ODMTaskResult):
        return (
            obj.workspace.user_id == request.referrer.id
            and obj.uuid == request.referrer.result_uuid
        )
