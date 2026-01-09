import hmac
import hashlib
from django.http import HttpRequest
from django.conf import settings


class NodeODMServiceAuth:
    HMAC_MESSAGE = "message"

    @staticmethod
    def generate_hmac_signature(message: str) -> hmac.HMAC:
        return hmac.new(
            settings.NODEODM_WEBHOOK_SECRET.encode(), message.encode(), hashlib.sha256
        ).hexdigest()

    def __call__(self, request: HttpRequest):
        signature = request.GET.get("signature")
        if not signature:
            return False

        expected = self.generate_hmac_signature(self.HMAC_MESSAGE)
        return hmac.compare_digest(signature, expected)
