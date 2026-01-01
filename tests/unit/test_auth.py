import hashlib
import hmac
import time

import pytest

from app.api.auth.authenticators import ServiceHMACAuth
from app.core.models.auth import AuthorizedService
from tests.factories import AuthorizedServiceFactory
from unittest.mock import Mock
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import AccessToken
from ninja_jwt.exceptions import AuthenticationFailed
from app.api.auth.authenticators import ServiceUserJWTAuth, ServiceUser

@pytest.mark.unit
def test_can_create_authorized_service(db):
    service = AuthorizedService.objects.create(
        name="gateway-a",
        api_key="key-123",
        api_secret="secret-456",
        allowed_scopes=["read:profile"],
    )
    assert service.name == "gateway-a"
    assert service.is_active is True


def test_factory_creates_valid_service(db):
    service = AuthorizedServiceFactory()
    assert service.pk
    assert len(service.api_key) >= 32


def test_api_key_is_unique(db):
    s1 = AuthorizedServiceFactory()
    s2 = AuthorizedServiceFactory()
    assert s1.api_key != s2.api_key


@pytest.mark.unit
def test_invalid_hmac_signature_is_rejected(rf, db):
    auth = ServiceHMACAuth()
    request = rf.post("/test/")

    service = AuthorizedServiceFactory()
    ts = str(int(time.time()))

    invalid_token = f"{service.api_key}:{ts}:tampered-signature"

    assert auth.authenticate(request, invalid_token) is None

@pytest.mark.unit
def test_valid_hmac_signature_returns_the_service(rf, db):
    auth = ServiceHMACAuth()
    request = rf.post("/test/")

    service = AuthorizedServiceFactory()
    ts = str(int(time.time()))

    message = f"{service.api_key}:{ts}:POST:/test/:".encode()

    signature = hmac.new(
        service.api_secret.encode(),
        message,
        hashlib.sha256,
    ).hexdigest()

    token = f"{service.api_key}:{ts}:{signature}"

    authenticated_service = auth.authenticate(request, token)
    
    assert authenticated_service == service
    assert request.service == service

@pytest.mark.unit
def test_hmac_timestamp_outside_allowed_window_is_rejected(rf, db):
    auth = ServiceHMACAuth()
    request = rf.post("/test/")

    service = AuthorizedServiceFactory()

    # Timestamp older than 5 minutes (301 seconds)
    ts = str(int(time.time()) - 301)

    message = f"{service.api_key}:{ts}:POST:/test/:".encode()

    signature = hmac.new(
        service.api_secret.encode(),
        message,
        hashlib.sha256,
    ).hexdigest()

    token = f"{service.api_key}:{ts}:{signature}"

    assert auth.authenticate(request, token) is None


class TestServiceUserJWTAuth:
    def test_authenticate_creates_service_user_with_correct_attributes(self, valid_token):
        auth = ServiceUserJWTAuth()

        request = Mock()
        authenticated_user = auth.authenticate(request, valid_token)

        assert authenticated_user is not None
        assert isinstance(authenticated_user, ServiceUser)
        assert authenticated_user.is_authenticated is True
        assert authenticated_user.is_anonymous is False

    def test_missing_user_id_returns_none(self):
        payload = {"scopes": ["test"], "exp": 9999999999, "iat": 1600000000}
        token = str(AccessToken(payload))

        auth = ServiceUserJWTAuth()
        request = Mock()

        result = auth.authenticate(request, token)
        assert result is None

    def test_invalid_or_expired_token_raises_authentication_failed(self):
        auth = ServiceUserJWTAuth()
        request = Mock()

        # Simulate AccessToken raising exception on invalid token
        with pytest.raises(AuthenticationFailed):
            auth.authenticate(request, "invalid.token.string")

    def test_service_user_has_expected_properties(self):
        user = ServiceUser(user_id=123, scopes=["a", "b"])

        assert user.is_active is True
        assert user.is_authenticated is True
        assert user.is_anonymous is False
        assert user.pk == 123
        assert user.id == 123
        assert user.scopes == ["a", "b"]
    