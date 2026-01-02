
from pydantic import Field, computed_field
from pathlib import Path
from enum import StrEnum, auto, unique

from .base import BaseSettingsMixin

@unique
class TusReplacementPolicy(StrEnum):
    OVERWRITE = auto()

@unique
class TusFileSecurityPolicy(StrEnum):
    RANDOM_SUFFIX = auto()


class TusSettingsMixin(BaseSettingsMixin):
    TUS_FILE_NAME_FORMAT: TusFileSecurityPolicy = Field(default=TusFileSecurityPolicy.RANDOM_SUFFIX)
    TUS_EXISTING_FILE: TusReplacementPolicy = Field(default=TusReplacementPolicy.OVERWRITE)

    @computed_field
    @property
    def TUS_MAX_FILE_SIZE(self) -> int:
        return 10 * 1024 * 1024

    @computed_field
    @property
    def TUS_UPLOAD_DIR(self) -> Path:
        return Path(self.MEDIA_ROOT) / 'uploads'

    @computed_field
    @property
    def TUS_DESTINATION_DIR(self) -> Path:
        return self.TUS_UPLOAD_DIR