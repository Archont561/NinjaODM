import pytest
from ninja_extra.testing import TestClient

from app.api import create_api
from app.config.settings.main import PydanticDjangoSettings


@pytest.fixture(scope="session")
def api_client():
    """Create a test client for the API"""
    return TestClient(create_api())


@pytest.fixture(scope="session")
def test_settings():
    return PydanticDjangoSettings(ENVIRONMENT="test")  # noqa


@pytest.fixture
def enable_db_access(db):
    """Automatically enable database access test"""
    pass
