import pytest
import hmac
import hashlib
import time
from django.urls import reverse
from tests.factories import AuthorizedServiceFactory


@pytest.mark.django_db
class TestInternalTokenObtainAuthorization:
    
    def _make_hmac_auth_header(self, service, method, path):
        ts = str(int(time.time()))
        message = f"{service.api_key}:{ts}:{method}:{path}".encode()
        signature = hmac.new(
            service.api_secret.encode(), message, hashlib.sha256
        ).hexdigest()
        return f"Bearer {service.api_key}:{ts}:{signature}"

    def test_authorized_service_can_obtain_token_pair(self, api_client):
        service = AuthorizedServiceFactory(is_active=True)

        url = "/internal/token/pair"
        payload = {
            "user_id": 5001,
            "scopes": ["read:profile", "write:data"]
        }
        auth_header = self._make_hmac_auth_header(service, "POST", url)

        response = api_client.post(
            url,
            json=payload,
            content_type="application/json",
            headers={
                "Authorization": auth_header
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "refresh" in data
        assert "access" in data
        assert data["refresh"]
        assert data["access"]

    def test_inactive_service_cannot_obtain_tokens(self, api_client):
        service = AuthorizedServiceFactory(is_active=False)

        url = "/internal/token/pair"
        payload = {"user_id": 1, "scopes": []}

        auth_header = self._make_hmac_auth_header(service, "POST", url)

        response = api_client.post(
            url,
            json=payload,
            content_type="application/json",
            headers={
                "Authorization": auth_header
            }
        )

        assert response.status_code in (401, 403)

    def test_no_auth_header_returns_401_or_403(self, api_client):
        url = "/internal/token/pair"
        payload = {"user_id": 1, "scopes": []}

        response = api_client.post(url, json=payload, content_type="application/json")

        assert response.status_code in (401, 403)

    def test_invalid_hmac_signature_returns_401_or_403(self, api_client):
        service = AuthorizedServiceFactory()

        url = "/internal/token/pair"
        payload = {"user_id": 1, "scopes": []}

        # Tampered signature
        bad_header = f"Bearer {service.api_key}:1234567890:bad-signature"

        response = api_client.post(
            url,
            json=payload,
            content_type="application/json",
            header={
                "Authorization": bad_header
            }
        )

        assert response.status_code in (401, 403)
    