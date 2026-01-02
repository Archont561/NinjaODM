from typing import Any, Dict, List
from pydantic import Field, computed_field

from pathlib import Path
from .base import BaseSettingsMixin

FILE_MIME_TYPE = str

class ODMSettingsMixin(BaseSettingsMixin):
    WORKSPACES_DIR_NAME: str = Field(default="workspaces")
    TASKS_DIR_NAME: str = Field(default="tasks")
    THUMBNAILS_DIR_NAME: str = Field(default="thumbnails")
    IMAGES_DIR_NAME: str = Field(default="images")
    GROUND_CONTROL_POINTS_FILE_NAME: str = Field(default="gcp_list.txt")

    ODM_CONTAINER_VOLUME: str = Field(...)
    ODM_CONTAINER_URL: str = Field(...)

    WORKSPACE_ALLOWED_FILE_MIME_TYPES: List[FILE_MIME_TYPE] = Field(default=[
        "image/jpeg", "image/png", "image/bmp",
        "image/webp", "image/tiff", "image/heif",
        "image/heic",
    ])

    @computed_field
    @property
    def WORKSPACES_DIR(self) -> Path:
        return self.DATA_DIR / self.WORKSPACES_DIR_NAME
    