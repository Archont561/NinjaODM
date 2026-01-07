import io
import pytest
import time
import hmac
import hashlib
import fakeredis
from unittest.mock import patch
from ninja_extra.testing import TestClient
from pytest_factoryboy import register
from PIL import Image as PILImage
from django.core.files.uploadedfile import SimpleUploadedFile
from ninja_jwt.tokens import AccessToken
from pathlib import Path

from app.api.api import create_api


from tests.factories import (
    WorkspaceFactory,
    ImageFactory,
    GroundControlPointFactory,
    ODMTaskFactory,
    ODMTaskResultFactory,
    AuthorizedServiceFactory,
)


register(WorkspaceFactory)
register(ImageFactory)
register(GroundControlPointFactory)
register(ODMTaskFactory)
register(ODMTaskResultFactory)
register(AuthorizedServiceFactory)


@pytest.fixture
def api_client():
    return TestClient(create_api())


@pytest.fixture
def valid_token():
    token = AccessToken()
    token["user_id"] = 999
    token["scopes"] = ["read:profile", "admin"]
    token["exp"] = 9999999999
    token["iat"] = 1600000000
    return token


@pytest.fixture(autouse=True)
def temp_media(tmp_path, settings):
    """
    Override MEDIA_ROOT for tests to a temporary folder.
    Automatically cleaned up after the test.
    """
    settings.MEDIA_ROOT = tmp_path
    yield tmp_path


@pytest.fixture
def temp_image_file(temp_media):
    """
    Creates a real temporary image file usable by Pillow.
    """
    image = PILImage.new("RGB", (300, 300), color="red")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    return SimpleUploadedFile(
        name="test.jpg",
        content=buffer.getvalue(),
        content_type="image/jpeg",
    )


def build_service_auth_header(
    *,
    api_key: str,
    api_secret: str,
    method: str,
    path: str,
    timestamp: int | None = None,
):
    timestamp = timestamp or int(time.time())
    message = f"{api_key}:{timestamp}:{method.upper()}:{path}".encode()

    signature = hmac.new(
        api_secret.encode(),
        message,
        hashlib.sha256,
    ).hexdigest()

    return f"Bearer {api_key}:{timestamp}:{signature}"


@pytest.fixture
def service_api_client(authorized_service_factory, api_client):
    service = authorized_service_factory()

    class AuthorizedClient:
        def request(self, method, path, **kwargs):
            headers = kwargs.pop("headers", {})

            headers["Authorization"] = build_service_auth_header(
                api_key=service.api_key,
                api_secret=service.api_secret,
                method=method,
                path=path,
            )

            return api_client.request(
                method,
                path,
                headers=headers,
                **kwargs,
            )

        def get(self, path, **kwargs):
            return self.request("GET", path, **kwargs)

        def post(self, path, **kwargs):
            return self.request("POST", path, **kwargs)

        def patch(self, path, **kwargs):
            return self.request("PATCH", path, **kwargs)

        def put(self, path, **kwargs):
            return self.request("PUT", path, **kwargs)

        def delete(self, path, **kwargs):
            return self.request("DELETE", path, **kwargs)

    return AuthorizedClient()


@pytest.fixture
def service_user_api_client(api_client, valid_token):
    class JWTClient:
        def __init__(self, api_client, token):
            self.api_client = api_client
            self.token = token

        def request(self, method, path, **kwargs):
            headers = kwargs.pop("headers", {})
            # ServiceUserJWTAuth expects 'Bearer <token>'
            headers["Authorization"] = f"Bearer {self.token}"
            return self.api_client.request(method, path, headers=headers, **kwargs)

        def get(self, path, **kwargs):
            return self.request("GET", path, **kwargs)

        def post(self, path, **kwargs):
            return self.request("POST", path, **kwargs)

        def put(self, path, **kwargs):
            return self.request("PUT", path, **kwargs)

        def patch(self, path, **kwargs):
            return self.request("PATCH", path, **kwargs)

        def delete(self, path, **kwargs):
            return self.request("DELETE", path, **kwargs)

    return JWTClient(api_client, valid_token)


@pytest.fixture
def mock_redis():
    server = fakeredis.FakeServer()
    async_redis = fakeredis.FakeAsyncRedis(server=server)
    sync_redis = fakeredis.FakeRedis(server=server)

    with patch("app.api.sse.aioredis.from_url", return_value=async_redis), \
         patch("django_redis.client.DefaultClient.get_client", return_value=sync_redis), \
         patch("django_redis.get_redis_connection", return_value=sync_redis):
        yield server
