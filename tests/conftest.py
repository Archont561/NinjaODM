import io
import pytest
import fakeredis
from unittest.mock import patch
from pytest_factoryboy import register
from PIL import Image as PILImage
from django.core.files.uploadedfile import SimpleUploadedFile
from ninja_jwt.tokens import AccessToken

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


@pytest.fixture
def mock_redis():
    server = fakeredis.FakeServer()
    async_redis = fakeredis.FakeAsyncRedis(server=server)
    sync_redis = fakeredis.FakeRedis(server=server)

    with (
        patch("app.api.sse.aioredis.from_url", return_value=async_redis),
        patch("django_redis.client.DefaultClient.get_client", return_value=sync_redis),
        patch("django_redis.get_redis_connection", return_value=sync_redis),
    ):
        yield server
