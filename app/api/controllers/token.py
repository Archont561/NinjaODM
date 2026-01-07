from ninja_extra import api_controller, route, http_post
from ninja import Schema, Body
from ninja.errors import HttpError
from injector import inject

from app.api.schemas.token import (
    TokenRequestInternal,
    TokenPairResponseInternal,
    AccessTokenResponseInternal,
    RefreshRequestInternal,
)
from app.api.services.token import TokenService
from app.api.auth.service import ServiceHMACAuth


@api_controller("internal/token", auth=ServiceHMACAuth(), tags=["token", "internal"])
class TokenControllerInternal:
    @inject
    def __init__(self, token_service: TokenService):
        self.token_service = token_service

    @http_post(
        "/pair",
        response=TokenPairResponseInternal,
    )
    def obtain_token(self, payload: TokenRequestInternal = Body(...)):
        return self.token_service.obtain_token(payload.dict())

    @http_post(
        "/refresh",
        response=AccessTokenResponseInternal,
    )
    def refresh_token(self, payload: RefreshRequestInternal = Body(...)):
        return self.token_service.refresh_token(payload.refresh)
