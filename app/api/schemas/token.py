from ninja import Schema
from typing import List


class TokenRequestInternal(Schema):
    user_id: int
    scopes: List[str] = []


class TokenPairResponseInternal(Schema):
    refresh: str
    access: str


class AccessTokenResponseInternal(Schema):
    access: str


class RefreshRequestInternal(Schema):
    refresh: str
