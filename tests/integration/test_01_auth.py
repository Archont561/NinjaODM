import pytest
import hmac
import hashlib
from django.utils import timezone
from ninja_extra.testing import TestClient

from app.api.controllers.token import TokenControllerInternal
from tests.utils import APITestSuite


# =========================================================================
# FIXTURES
# =========================================================================


@pytest.fixture
def token_client():
    """Unauthenticated client for Token API."""
    return TestClient(TokenControllerInternal)


@pytest.fixture
def active_service(authorized_service_factory):
    """Active authorized service."""
    return authorized_service_factory(is_active=True)


@pytest.fixture
def inactive_service(authorized_service_factory):
    """Inactive authorized service."""
    return authorized_service_factory(is_active=False)


def make_hmac_header(service, method: str, path: str, invalid: bool = False) -> dict:
    """Generate HMAC auth header."""
    ts = str(int(timezone.now().timestamp()))
    message = f"{service.api_key}:{ts}:{method}:{path}".encode()

    if invalid:
        signature = "bad-signature"
    else:
        signature = hmac.new(
            service.api_secret.encode(), message, hashlib.sha256
        ).hexdigest()

    return {"Authorization": f"Bearer {service.api_key}:{ts}:{signature}"}


# -------------------------
# Header Factories
# -------------------------


@pytest.fixture
def active_service_auth_headers(active_service):
    """Auth headers for active service."""
    return make_hmac_header(active_service, "POST", "/pair")


@pytest.fixture
def inactive_service_auth_headers(inactive_service):
    """Auth headers for inactive service."""
    return make_hmac_header(inactive_service, "POST", "/pair")


@pytest.fixture
def invalid_signature_headers(active_service):
    """Invalid signature headers."""
    return make_hmac_header(active_service, "POST", "/pair", invalid=True)


# -------------------------
# Dummy Factory (for actions that don't need objects)
# -------------------------


@pytest.fixture
def no_object_factory():
    """Dummy factory that returns None-like object."""

    class DummyObject:
        uuid = None

    return lambda: DummyObject()


# -------------------------
# Assertions
# -------------------------


@pytest.fixture
def assert_token_pair():
    """Assert valid token pair response."""

    def assertion(obj, resp):
        assert resp.status_code == 200
        data = resp.json()
        assert "refresh" in data
        assert "access" in data
        assert data["refresh"]
        assert data["access"]
        return True

    return assertion


# =========================================================================
# TEST SUITE
# =========================================================================


@pytest.mark.django_db
@pytest.mark.freeze_time("2026-01-20 12:00:00")
class TestTokenAPI(APITestSuite):
    """
    Token API tests.

    Covers:
    - Token pair generation with valid service auth
    - Inactive service denied
    - Missing auth denied
    - Invalid signature denied
    """

    tests = {
        # ===== DEFAULTS =====
        "model": None,
        "endpoint": "/",
        "factory": "no_object_factory",
        "client": "token_client",
        # ===== ACTIONS =====
        "actions": {
            "obtain_pair": {
                "url": "/pair",
                "method": "post",
                "scenarios": [
                    # Active service - success
                    {
                        "name": "active_service_success",
                        "payload": {
                            "user_id": "user_5001",
                            "scopes": ["read:profile", "write:data"],
                        },
                        "headers": "active_service_auth_headers",
                        "assert": "assert_token_pair",
                    },
                    # Inactive service - denied
                    {
                        "name": "inactive_service_denied",
                        "payload": {"user_id": "user_1", "scopes": []},
                        "headers": "inactive_service_auth_headers",
                        "expected_status": [401, 403],
                        "access_denied": True,
                    },
                    # No auth header - denied
                    {
                        "name": "no_auth_denied",
                        "payload": {"user_id": "user_1", "scopes": []},
                        "expected_status": [401, 403],
                        "access_denied": True,
                    },
                    # Invalid signature - denied
                    {
                        "name": "invalid_signature_denied",
                        "payload": {"user_id": "user_1", "scopes": []},
                        "headers": "invalid_signature_headers",
                        "expected_status": [401, 403],
                        "access_denied": True,
                    },
                ],
            },
        },
    }
