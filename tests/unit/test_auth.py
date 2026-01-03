import hashlib
import hmac
import time
import pytest
from app.api.auth.service import ServiceHMACAuth
from app.api.auth.user import ServiceUserJWTAuth
from app.api.constants.user import ServiceUser
from app.api.models.service import AuthorizedService


@pytest.mark.django_db
class TestAuthorizedService:
    def test_factory_creates_valid_service(self, authorized_service_factory):
        service = authorized_service_factory()
        assert service.pk
        assert len(service.api_key) >= 32

    def test_api_key_is_unique(self, authorized_service_factory):
        s1 = authorized_service_factory()
        s2 = authorized_service_factory()
        assert s1.api_key != s2.api_key

    def test_invalid_hmac_signature_is_rejected(self, rf, authorized_service_factory):
        auth = ServiceHMACAuth()
        request = rf.post("/test/")

        service = authorized_service_factory()
        ts = str(int(time.time()))

        invalid_token = f"{service.api_key}:{ts}:tampered-signature"

        assert auth.authenticate(request, invalid_token) is None

    def test_valid_hmac_signature_returns_the_service(self, rf, authorized_service_factory):
        auth = ServiceHMACAuth()
        request = rf.post("/test/")

        service = authorized_service_factory()
        ts = str(int(time.time()))

        message = f"{service.api_key}:{ts}:POST:/test/".encode()

        signature = hmac.new(
            service.api_secret.encode(),
            message,
            hashlib.sha256,
        ).hexdigest()

        token = f"{service.api_key}:{ts}:{signature}"

        authenticated_service = auth.authenticate(request, token)

        assert authenticated_service == service
        assert request.service == service

    def test_hmac_timestamp_outside_allowed_window_is_rejected(self, rf, authorized_service_factory):
        auth = ServiceHMACAuth()
        request = rf.post("/test/")

        service = authorized_service_factory()

        # Timestamp older than 5 minutes (301 seconds)
        ts = str(int(time.time()) - 301)

        message = f"{service.api_key}:{ts}:POST:/test/".encode()

        signature = hmac.new(
            service.api_secret.encode(),
            message,
            hashlib.sha256,
        ).hexdigest()

        token = f"{service.api_key}:{ts}:{signature}"

        assert auth.authenticate(request, token) is None


class TestServiceUserJWTAuth:
    def test_authenticate_creates_service_user_with_correct_attributes(self, rf, valid_token):
        auth = ServiceUserJWTAuth()

        request = rf.get("/")
        authenticated_user = auth.authenticate(request, str(valid_token))

        assert authenticated_user is not None
        assert isinstance(authenticated_user, ServiceUser)
        assert authenticated_user.is_authenticated is True
        assert authenticated_user.is_anonymous is False

    def test_missing_user_id_returns_none(self, rf, valid_token):
        del valid_token["user_id"]

        auth = ServiceUserJWTAuth()
        request = rf.get("/")

        result = auth.authenticate(request, str(valid_token))
        assert result is None

    def test_service_user_has_expected_properties(self):
        user = ServiceUser(user_id=123, scopes=["a", "b"])

        assert user.is_active is True
        assert user.is_authenticated is True
        assert user.is_anonymous is False
        assert user.pk == 123
        assert user.id == 123
        assert user.scopes == ["a", "b"]
    