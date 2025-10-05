from pathlib import Path
import sys
from pydantic import computed_field
from .base import BaseSettingsMixin


class GISSettingsMixin(BaseSettingsMixin):

    @computed_field
    @property
    def PIXI_ENV_PATH(self) -> Path:
        return self.PROJECT_DIR / ".pixi" / "envs" / self.ENVIRONMENT

    @staticmethod
    def _get_library_path(env_path: Path, lib_name: str) -> Path:
        """Return platform-specific library path."""
        if sys.platform == "win32":
            return env_path / "Library" / "bin" / f"{lib_name}.dll"
        elif sys.platform == "darwin":  # macOS
            return env_path / "lib" / f"lib{lib_name}.dylib"
        else:  # Linux
            return env_path / "lib" / f"lib{lib_name}.so"

    @computed_field
    @property
    def GDAL_LIBRARY_PATH(self) -> str:
        return str(self._get_library_path(self.PIXI_ENV_PATH, "gdal"))

    @computed_field
    @property
    def GEOS_LIBRARY_PATH(self) -> str:
        return str(self._get_library_path(self.PIXI_ENV_PATH, "geos_c"))

    @computed_field
    @property
    def PROJ_LIBRARY_PATH(self) -> str:
        return str(self._get_library_path(self.PIXI_ENV_PATH, "proj"))

    @computed_field
    @property
    def SPATIALITE_LIBRARY_PATH(self) -> str:
        """SpatiaLite has different naming convention."""
        if sys.platform == "win32":
            return str(self.PIXI_ENV_PATH / "Library" / "lib" / "mod_spatialite.lib")
        else:
            return str(self._get_library_path(self.PIXI_ENV_PATH, "mod_spatialite"))