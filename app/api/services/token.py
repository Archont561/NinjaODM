from typing import Dict, Any
from ninja_jwt.tokens import RefreshToken


class TokenService:
    def obtain_token(self, payload: Dict[str, Any]):
        refresh = RefreshToken()
        refresh["user_id"] = payload["user_id"]
        refresh["scopes"] = payload["scopes"]  # Custom claim for scopes

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

    def refresh_token(self, refresh_token: str):
        refresh = RefreshToken(refresh_token)
        return {"access": str(refresh.access_token)}
