from pathlib import Path

from pydantic import computed_field
from .base import BaseSettingsMixin


class GISSettingsMixin(BaseSettingsMixin):

    @computed_field
    @property
    def PIXI_ENV_PATH(self) -> Path:
        return self.PROJECT_DIR / ".pixi" / "envs" / self.ENVIRONMENT

    @computed_field
    @property
    def PIXI_ENV_PATH_LIBRARY_BIN(self) -> Path:
        return self.PIXI_ENV_PATH / "Library" / "bin"

    @computed_field
    @property
    def PIXI_ENV_PAth_LIBRARY_LIB(self) -> Path:
        return self.PIXI_ENV_PATH / "Library" / "lib"

    @computed_field
    @property
    def GDAL_LIBRARY_PATH(self) -> Path:
        return self.PIXI_ENV_PATH_LIBRARY_BIN / "gdal.dll"

    @computed_field
    @property
    def SPATIALITE_LIBRARY_PATH(self) -> Path:
        return self.PIXI_ENV_PAth_LIBRARY_LIB / "mod_spatialite.lib"
