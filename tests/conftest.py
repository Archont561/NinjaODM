import pytest
from ninja_extra.testing import TestClient
from app.config.settings.main import PydanticDjangoSettings

from app.api import api


@pytest.fixture
def api_client(scope="session"):
    """Create a test client for the API"""
    api.auto_discover_controllers()
    return TestClient(api)


@pytest.fixture(scope="session")
def test_settings():
    return PydanticDjangoSettings(ENVIRONMENT="test")  # noqa
