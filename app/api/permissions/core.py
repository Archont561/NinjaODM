from app.api.constants.user import ServiceUser
from app.api.models.service import AuthorizedService


class IsAuthorizedService(permissions.BasePermission):
    def has_permission(self, request, controller):
        return isinstance(getattr(request, "service"), AuthorizedService)


class IsServiceUser(permissions.BasePermission):
    def has_permission(self, request, controller):
        return isinstance(getattr(request, "user"), ServiceUser)
