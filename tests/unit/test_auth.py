import hashlib
import hmac
import time

import pytest

from app.api.auth.authenticators import ServiceHMACAuth
from app.core.models.auth import AuthorizedService
from tests.factories import AuthorizedServiceFactory


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
