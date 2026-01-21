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
from tests.server_mocks import NodeODMMockHTTPServer


def pytest_collection_modifyitems(session, config, items):
    # sort items by module filename and then by function name
    items.sort(key=lambda item: (item.module.__name__, item.name))


register(WorkspaceFactory)
register(ImageFactory)
register(GroundControlPointFactory)
register(ODMTaskFactory)
register(ODMTaskResultFactory)
register(AuthorizedServiceFactory)


@pytest.fixture
def valid_token():
    token = AccessToken()
    token["user_id"] = "user_999"
    token["scopes"] = ["read:profile", "admin"]
    token["exp"] = 9999999999
    token["iat"] = 1600000000
    return token


@pytest.fixture(autouse=True)
def test_settings(tmp_path_factory, settings):
    settings.MEDIA_ROOT = tmp_path_factory.mktemp("MEDIA_ROOT")
    settings.DATA_DIR = tmp_path_factory.mktemp("DATA_DIR")
    settings.STATIC_ROOT = tmp_path_factory.mktemp("STATIC_ROOT")
    settings.TASKS_DIR = settings.DATA_DIR / "tasks"
    settings.TUS_UPLOAD_DIR = settings.MEDIA_ROOT / "uploads"
    settings.TUS_DESTINATION_DIR = settings.TUS_UPLOAD_DIR
    settings.TUS_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    yield


@pytest.fixture
def temp_image_file():
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


@pytest.fixture
def mock_task_on_task_create():
    with patch("app.api.services.task.on_task_create") as mock:
        yield mock


@pytest.fixture
def mock_task_on_task_pause():
    with patch("app.api.services.task.on_task_pause") as mock:
        yield mock


@pytest.fixture
def mock_task_on_task_resume():
    with patch("app.api.services.task.on_task_resume") as mock:
        yield mock


@pytest.fixture
def mock_task_on_task_cancel():
    with patch("app.api.services.task.on_task_cancel") as mock:
        yield mock


@pytest.fixture
def mock_task_on_task_nodeodm_webhook():
    with patch("app.api.services.task.on_task_nodeodm_webhook") as mock:
        yield mock


@pytest.fixture
def mock_task_on_task_finish():
    with patch("app.api.services.task.on_task_finish") as mock:
        yield mock


@pytest.fixture
def mock_task_on_task_failure():
    with patch("app.api.services.task.on_task_failure") as mock:
        yield mock


@pytest.fixture
def mock_task_on_workspace_images_uploaded():
    with patch("app.api.services.workspace.on_workspace_images_uploaded") as mock:
        yield mock


@pytest.fixture
def mock_odm_server(httpserver, settings):
    mock_server = NodeODMMockHTTPServer(httpserver).register_routes()
    settings.NODEODM_URL = mock_server.base_url
    settings.NINJAODM_BASE_URL = "https://ninjaodm.example.com"
    return mock_server
