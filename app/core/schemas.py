from ninja import Schema
from typing import Optional


class MessageSchema(Schema):
    message: str


class ErrorSchema(Schema):
    error: str
    details: Optional[str] = None
