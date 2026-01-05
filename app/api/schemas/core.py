from ninja import Schema
from typing import Optional, Dict


class MessageSchema(Schema):
    message: str


class ErrorSchema(Schema):
    error: str
    details: Optional[str] = None


class HealthSchema(Schema):
    status: str
    timestamp: float
    mixins: Dict[str, str]
