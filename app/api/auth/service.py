import hmac
import hashlib
from typing import Optional, Tuple

from ninja.security import HttpBearer
from django.http import HttpRequest
from django.utils import timezone

from app.api.models.service import AuthorizedService


class ServiceHMACAuth(HttpBearer):
    """
    Django Ninja Service HMAC Bearer Auth

    Header:
        Authorization: Bearer <api_key>:<timestamp>:<signature>
    """

    def authenticate(self, request, token: str) -> Optional[AuthorizedService]:
        if not token:
            return None

        parsed = self._parse_token(token)
        if not parsed:
            return None

        api_key, timestamp, signature = parsed

        if not self._is_timestamp_valid(timestamp):
            return None

        service = self._get_service(api_key)
        if not service:
            return None

        message = self._build_message(request, api_key, timestamp)
        if not self._is_signature_valid(service.api_secret, message, signature):
            return None

        request.service = service
        return service

    # =====================
    # Private helpers
    # =====================

    def _parse_token(self, token: str) -> Optional[Tuple[str, int, str]]:
        parts = token.split(":", 2)
        if len(parts) != 3:
            return None

        api_key, timestamp_str, signature = parts
        try:
            return api_key, int(timestamp_str), signature
        except ValueError:
            return None

    def _is_timestamp_valid(self, timestamp: int, window: int = 300) -> bool:
        now = int(timezone.now().timestamp())
        return abs(now - timestamp) <= window

    def _get_service(self, api_key: str) -> Optional[AuthorizedService]:
        try:
            return AuthorizedService.objects.only("api_secret").get(
                api_key=api_key,
                is_active=True,
            )
        except AuthorizedService.DoesNotExist:
            return None

    def _build_message(
        self, request: HttpRequest, api_key: str, timestamp: int
    ) -> bytes:
        method = request.method.upper()

        return f"{api_key}:{timestamp}:{method}:{request.path}".encode()

    def _is_signature_valid(
        self,
        secret: str,
        message: bytes,
        provided_signature: str,
    ) -> bool:
        expected = hmac.new(
            secret.encode(),
            message,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, provided_signature)
