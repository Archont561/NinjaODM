import pytest
import hmac
import hashlib
import time


@pytest.mark.django_db
class TestTokenObtainAuthorization:

    def _make_hmac_auth_header(self, service, method, path):
        ts = str(int(time.time()))
        message = f"{service.api_key}:{ts}:{method}:{path}".encode()
        signature = hmac.new(
            service.api_secret.encode(), message, hashlib.sha256
        ).hexdigest()
        return f"Bearer {service.api_key}:{ts}:{signature}"

    def test_authorized_service_can_obtain_token_pair(self, api_client, authorized_service_factory):
        service = authorized_service_factory(is_active=True)
        url = "/internal/token/pair"
        response = api_client.post(
            url,
            json={
                "user_id": 5001,
                "scopes": ["read:profile", "write:data"]
            },
            content_type="application/json",
            headers={
                "Authorization": self._make_hmac_auth_header(service, "POST", url)
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "refresh" in data
        assert "access" in data
        assert data["refresh"]
        assert data["access"]

    def test_inactive_service_cannot_obtain_tokens(self, api_client, authorized_service_factory):
        service = authorized_service_factory(is_active=False)
        url = "/internal/token/pair"
        response = api_client.post(
            url,
            json={"user_id": 1, "scopes": []},
            content_type="application/json",
            headers={
                "Authorization": self._make_hmac_auth_header(service, "POST", url)
            }
        )

        assert response.status_code in (401, 403)

    def test_no_auth_header_returns_401_or_403(self, api_client):
        response = api_client.post(
            "/internal/token/pair",
            json={"user_id": 1, "scopes": []},
            content_type="application/json"
        )

        assert response.status_code in (401, 403)

    def test_invalid_hmac_signature_returns_401_or_403(self, api_client, authorized_service_factory):
        service = authorized_service_factory()
        response = api_client.post(
            "/internal/token/pair",
            json={"user_id": 1, "scopes": []},
            content_type="application/json",
            header={
                "Authorization": f"Bearer {service.api_key}:1234567890:bad-signature"
            }
        )

        assert response.status_code in (401, 403)
