from ninja import Schema
from typing import List

class InternalTokenRequest(Schema):
    user_id: int
    scopes: List[str] = []

class InternalTokenPairOut(Schema):
    refresh: str
    access: str

class InternalAccessTokenOut(Schema):
    access: str

class InternalRefreshRequest(Schema):
    refresh: str