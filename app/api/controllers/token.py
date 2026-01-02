from ninja_extra import api_controller, route, http_post
from ninja import Schema, Body
from ninja.errors import HttpError
from injector import inject

from app.api.schemas.token import (
    InternalTokenRequest,
    InternalTokenPairOut,
    InternalAccessTokenOut,
    InternalRefreshRequest,
)
from app.api.services.token import InternalTokenService
from app.api.auth.service import ServiceHMACAuth


@api_controller("internal/token", auth=ServiceHMACAuth(), tags=["internal_token"])
class InternalTokenController:
    @inject
    def __init__(self, internal_token_service: InternalTokenService):
        self.internal_token_service = internal_token_service

    @http_post(
        "/pair",
        response=InternalTokenPairOut,
        url_name="token_obtain_pair",
        operation_id="token_obtain_pair",
    )
    def obtain_token(self, payload: InternalTokenRequest = Body(...)):
        return self.internal_token_service.obtain_token(payload)

    @http_post(
        "/refresh",
        response=InternalAccessTokenOut,
        url_name="token_refresh",
        operation_id="token_refresh",
    )
    def refresh_token(self, payload: InternalRefreshRequest = Body(...)):
        return self.internal_token_service.refresh_token(payload.refresh)
    