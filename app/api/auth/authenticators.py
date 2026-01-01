import pytest

@pytest.mark.unit
def test_can_create_authorized_service(db):
    from server_b.models import AuthorizedService
    service = AuthorizedService.objects.create(
        name="gateway-a",
        api_key="key-123",
        api_secret="secret-456",
        allowed_scopes=["read:profile"]
    )
    assert service.name == "gateway-a"
    assert service.is_active is True