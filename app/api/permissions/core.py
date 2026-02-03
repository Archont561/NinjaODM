from ninja_extra import permissions
from app.api.constants.user import ServiceUser
from app.api.models.service import AuthorizedService


class IsAuthorizedService(permissions.BasePermission):
    def has_permission(self, request, controller):
        return isinstance(getattr(request, "service", None), AuthorizedService)

    def has_object_permission(self, request, controller, obj):
        return self.has_permission(request, controller)


class IsServiceUser(permissions.BasePermission):
    def has_permission(self, request, controller):
        return isinstance(getattr(request, "user", None), ServiceUser)

    def has_object_permission(self, request, controller, obj):
        return self.has_permission(request, controller)


class IsReferrer(permissions.BasePermission):
    def has_permission(self, request, controller):
        return isinstance(getattr(request, "referrer", None), ServiceUser)

    def has_object_permission(self, request, controller, obj):
        return self.has_permission(request, controller)


class BaseObjectPermission(permissions.BasePermission):
    def has_permission(self, request, controller):
        return True

    def has_object_permission(self, request, controller, obj):
        raise NotImplementedError