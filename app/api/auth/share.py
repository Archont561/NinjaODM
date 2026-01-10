from uuid import UUID
from ninja.security import APIKeyQuery
from ninja_jwt.authentication import JWTBaseAuthentication
from ninja_jwt.exceptions import InvalidToken, TokenError
from django.http import HttpRequest

from app.api.constants.token import ShareToken
from app.api.constants.user import ServiceUser


class ShareResultsApiKeyAuth(APIKeyQuery):
    param_name = "api_key"

    def authenticate(self, request: HttpRequest, token: str):
        try:
            validated_share_token = ShareToken(token)
        except TokenError:
            return False
        
        user_id = validated_share_token.get("shared_by_user_id")
        result_uuid = validated_share_token.get("result_uuid")

        if user_id is None:
            return False

        service_user = ServiceUser(user_id=int(user_id), scopes=[])
        setattr(service_user, "result_uuid", UUID(result_uuid))
        setattr(request, "referer", service_user)
        return True
