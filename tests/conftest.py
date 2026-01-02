import pytest
from ninja_extra.testing import TestClient

from app.api.api import create_api
from app.config.settings.main import get_settings
from ninja_jwt.tokens import AccessToken


@pytest.fixture(scope="session")
def test_settings():
    return get_settings()


@pytest.fixture(scope="session")
def test_settings():
    return get_settings()


@pytest.fixture(scope="session")
def api_client():
    """Create a test client for the API"""
    return TestClient(create_api())


# ========= Auth fixtures =========
@pytest.fixture
def valid_token():
    token = AccessToken()
    token["user_id"] = 999
    token["scopes"] = ["read:profile", "admin"]
    token["exp"] = 9999999999
    token["iat"] = 1600000000
    return token
    
    