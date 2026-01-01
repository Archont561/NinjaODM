import pytest
from app.core.models.auth import AuthorizedService
from tests.factories import AuthorizedServiceFactory

@pytest.mark.unit
def test_can_create_authorized_service(db):
    service = AuthorizedService.objects.create(
        name="gateway-a",
        api_key="key-123",
        api_secret="secret-456",
        allowed_scopes=["read:profile"]
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