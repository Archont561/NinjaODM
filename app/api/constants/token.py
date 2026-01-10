from __future__ import annotations
from datetime import timedelta
from typing import Any, Optional
from ninja_jwt.tokens import Token

from app.api.models.result import ODMTaskResult
from app.api.constants.user import ServiceUser


class ShareToken(Token):
    token_type: str = "share"
    lifetime: timedelta = timedelta(hours=48)
    
    @classmethod
    def for_result(
        cls, 
        result: ODMTaskResult, 
        expires_in_hours: int = 48
    ) -> ShareToken:
        token = cls()
        if expires_in_hours != 48:
            custom_lifetime = timedelta(hours=expires_in_hours)
            token.set_exp(from_time=token.current_time, lifetime=custom_lifetime)
        
        token['result_uuid'] = str(result.uuid)
        token['shared_by_user_id'] = result.workspace.user_id
        return token
    