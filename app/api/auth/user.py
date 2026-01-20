from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import AccessToken
from ninja_jwt.exceptions import TokenError
from django.http import HttpRequest

from app.api.constants.user import ServiceUser


class ServiceUserJWTAuth(JWTAuth):
    """
    Custom authentication that creates a ServiceUser from token claims.
    """

    def authenticate(self, request: HttpRequest, token: str):
        try:
            validated_token = AccessToken(token)
        except TokenError:
            return None

        user_id = validated_token.get("user_id")
        scopes = validated_token.get("scopes", [])

        if user_id is None:
            return None

        service_user = ServiceUser(user_id=user_id, scopes=scopes)
        request.user = service_user
        return service_user
