from typing import Optional
from ninja import Schema
from pydantic import Field


class TusBaseHeaders(Schema):
    tus_resumable: str = Field(
        ..., alias="Tus-Resumable", description="TUS Protocol version (1.0.0)"
    )


class TusPostHeaders(TusBaseHeaders):
    upload_length: int = Field(
        ..., alias="Upload-Length", description="Total size of file in bytes"
    )
    upload_metadata: Optional[str] = Field(
        None, alias="Upload-Metadata", description="Base64 encoded metadata"
    )


class TusPatchHeaders(TusBaseHeaders):
    upload_offset: int = Field(
        ..., alias="Upload-Offset", description="The byte offset of the chunk"
    )
    content_type: str = Field("application/offset+octet-stream", alias="Content-Type")
