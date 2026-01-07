
import time
import hmac
import hashlib
from typing import Literal
from enum import Enum
from ninja_extra.testing import TestClient, TestAsyncClient
from ninja_jwt.tokens import AccessToken
from .factories import AuthorizedServiceFactory


class AuthStrategy:
    def apply(self, method: str, path: str, headers: dict) -> None:
        raise NotImplementedError


class ServiceAuth(AuthStrategy):
    def __init__(self):
        self.service = AuthorizedServiceFactory()

    def build_service_auth_header(
        self,
        method: str,
        path: str,
        timestamp: int | None = None,
    ):
        timestamp = timestamp or int(time.time())
        message = f"{self.service.api_key}:{timestamp}:{method.upper()}:{path}".encode()

        signature = hmac.new(
            self.service.api_secret.encode(),
            message,
            hashlib.sha256,
        ).hexdigest()

        return f"Bearer {self.service.api_key}:{timestamp}:{signature}"

    def apply(self, method: str, path: str, headers: dict):
        headers["Authorization"] = self.build_service_auth_header(
            method=method,
            path=path,
        )


class JWTAuth(AuthStrategy):
    def __init__(self):
        self.token = AccessToken()
        self.token["user_id"] = 999
        self.token["scopes"] = ["*"]
        self.token["exp"] = 9999999999
        self.token["iat"] = 1600000000

    def apply(self, method: str, path: str, headers: dict):
        headers["Authorization"] = f"Bearer {self.token}"


class AuthStrategyEnum(Enum):
    service = ServiceAuth
    jwt = JWTAuth


class TestClientAuthenticationMixin:
    def __init__(self, *args, auth: AuthStrategyEnum, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth = auth.value()

    def _request(self, *args, **kwargs):
        headers = kwargs.pop("headers", {})
        method, path = args[:2]
        self.auth.apply(method, path, headers)
        return super().request(*args, headers=headers, **kwargs)


class AuthenticatedTestClient(TestClientAuthenticationMixin, TestClient):
    def request(self, *args, **kwargs):
        return self._request(*args, **kwargs)


class AuthenticatedTestAsyncClient(TestClientAuthenticationMixin, TestAsyncClient):
    def request(self, *args, **kwargs):
        return self._request(*args, **kwargs)
