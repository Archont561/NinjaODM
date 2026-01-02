import pytest
from ninja_extra.testing import TestClient
from pytest_factoryboy import register

from ninja_jwt.tokens import AccessToken
from pathlib import Path

from app.api.api import create_api
from app.config.settings.main import get_settings


from tests.factories import WorkspaceFactory, ImageFactory


register(WorkspaceFactory)
register(ImageFactory)


@pytest.fixture(scope="session")
def test_settings():
    return get_settings()


@pytest.fixture(scope="session")
def api_client():
    """Create a test client for the API"""
    return TestClient(create_api())


@pytest.fixture
def valid_token():
    token = AccessToken()
    token["user_id"] = 999
    token["scopes"] = ["read:profile", "admin"]
    token["exp"] = 9999999999
    token["iat"] = 1600000000
    return token


@pytest.fixture
def temp_media(tmp_path, settings):
    """
    Override MEDIA_ROOT for tests to a temporary folder.
    Automatically cleaned up after the test.
    """
    settings.MEDIA_ROOT = tmp_path
    yield tmp_path