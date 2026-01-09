from __future__ import annotations
from pathlib import Path
from enum import auto, unique, Enum, StrEnum, IntEnum
from typing import (
    Optional,
    FrozenSet,
    List,
    Tuple,
    Union,
    Dict,
)


class ChoicesMixin(Enum):
    @property
    def label(self) -> str:
        source = self.value if isinstance(self.value, str) else self.name
        return source.replace("_", " ").title()

    @classmethod
    def choices(cls) -> List[Tuple[Union[int, str], str]]:
        return [(member.value, member.label) for member in cls]

    def __str__(self) -> str:
        return self.name.lower()


@unique
class ODMTaskStatus(ChoicesMixin, StrEnum):
    QUEUED = auto()
    RUNNING = auto()
    PAUSING = auto()
    PAUSED = auto()
    RESUMING = auto()
    CANCELLING = auto()
    FINISHING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

    @classmethod
    def terminal_states(cls) -> FrozenSet[ODMTaskStatus]:
        return frozenset(
            {
                cls.FAILED,
                cls.COMPLETED,
                cls.CANCELLED,
            }
        )

    @classmethod
    def non_terminal_states(cls) -> FrozenSet[ODMTaskStatus]:
        return frozenset(set(cls) - cls.terminal_states())

    def is_terminal(self) -> bool:
        return self in self.terminal_states()


@unique
class NodeODMTaskStatus(IntEnum):
    QUEUED = 10
    RUNNING = 20
    FAILED = 30
    COMPLETED = 40
    CANCELED = 50


ODM_TASK_RESULT_RELATIVE_PATHS_MAPPING: Dict[str, Path] = {
        "POINT_CLOUD_PLY": Path("odm_georeferencing") / "odm_georeferenced_model.ply",
        "POINT_CLOUD_LAZ": Path("odm_georeferencing") / "odm_georeferenced_model.laz",
        "POINT_CLOUD_CSV": Path("odm_georeferencing") / "odm_georeferenced_model.csv",
        "TEXTURED_MODEL": Path("odm_texturing") / "odm_textured_model.obj",
        "TEXTURED_MODEL_GEO": Path("odm_texturing") / "odm_textured_model_geo.obj",
        "ORTHOPHOTO_GEOTIFF": Path("odm_orthophoto") / "odm_orthophoto.tif",
        "ORTHOPHOTO_WEBP": Path("odm_orthophoto") / "odm_orthophoto.webp",
        "DSM": Path("odm_dem") / "dsm.tif",
        "DTM": Path("odm_dem") / "dtm.tif",
        "REPORT": Path("odm_georeferencing") / "odm_georeferencing_log.txt",
    }


@unique
class ODMTaskResultType(ChoicesMixin, StrEnum):
    POINT_CLOUD_PLY = auto()
    POINT_CLOUD_LAZ = auto()
    POINT_CLOUD_CSV = auto()
    TEXTURED_MODEL = auto()
    TEXTURED_MODEL_GEO = auto()
    ORTHOPHOTO_GEOTIFF = auto()
    ORTHOPHOTO_WEBP = auto()
    DSM = auto()
    DTM = auto()
    REPORT = auto()

    @property
    def relative_path(self) -> Path:
        try:
            return ODM_TASK_RESULT_RELATIVE_PATHS_MAPPING[self.name]
        except KeyError as exc:
            raise NotImplementedError(
                f"No relative path defined for {self}"
            ) from exc


ODM_PROCESSING_STAGE_RESULTS_MAPPING: Dict[str, List[ODMTaskResultType]] = {
        "MVS_TEXTURING": [ODMTaskResultType.TEXTURED_MODEL],
        "ODM_GEOREFERENCING": [
            ODMTaskResultType.TEXTURED_MODEL_GEO,
            ODMTaskResultType.POINT_CLOUD_PLY,
            ODMTaskResultType.POINT_CLOUD_LAZ,
            ODMTaskResultType.POINT_CLOUD_CSV,
        ],
        "ODM_DEM": [
            ODMTaskResultType.DSM,
            ODMTaskResultType.DTM,
        ],
        "ODM_ORTHOPHOTO": [
            ODMTaskResultType.ORTHOPHOTO_GEOTIFF,
            ODMTaskResultType.ORTHOPHOTO_WEBP,
        ],
        "ODM_REPORT": [ODMTaskResultType.REPORT],
    }

class ODMProcessingStage(ChoicesMixin, StrEnum):
    DATASET = auto()
    SPLIT = auto()
    MERGE = auto()
    OPENSFM = auto()
    OPENMVS = auto()
    ODM_FILTERPOINTS = auto()
    ODM_MESHING = auto()
    MVS_TEXTURING = auto()
    ODM_GEOREFERENCING = auto()
    ODM_DEM = auto()
    ODM_ORTHOPHOTO = auto()
    ODM_REPORT = auto()
    ODM_POSTPROCESS = auto()

    @property
    def next_stage(self) -> Optional[ODMProcessingStage]:
        stages = list(type(self))
        try:
            return stages[stages.index(self) + 1]
        except IndexError:
            return None

    @property
    def previous_stage(self) -> Optional[ODMProcessingStage]:
        stages = list(type(self))
        try:
            return stages[stages.index(self) - 1]
        except IndexError:
            return None

    @property
    def stage_results(self) -> List[ODMTaskResultType]:
        try:
            return ODM_PROCESSING_STAGE_RESULTS_MAPPING[self.name]
        except KeyError:
            return []


ODM_QUALITY_OPTION_MAPPING: Dict[str, Dict[str, Dict[str, str | int | float | bool]]] = {
    "ULTRA_HIGH": {
        "dataset": {
            "gps-accuracy": 1.0,
        },
        "sfm": {
            "feature-quality": "ultra",
            "feature-type": "sift",
            "matcher-type": "flann",
            "pc-quality": "ultra",
            "min-num-features": 40000,
            "use-hybrid-bundle-adjustment": False,
        },
        "filterpoints": {
            "auto-boundary": True,
            "pc-sample": 0.0,
        },
        "meshing": {
            "mesh-octree-depth": 13,
            "mesh-size": 2_000_000,
        },
        "texturing": {
            "texturing-skip-global-seam-leveling": False,
        },
        "dem": {
            "dem-resolution": 2.0,
            "dem-decimation": 1,
        },
        "orthophoto": {
            "orthophoto-resolution": 2.0,
            "orthophoto-compression": "deflate",
        },
    },

    "HIGH": {
        "dataset": {
            "gps-accuracy": 3.0,
        },
        "sfm": {
            "feature-quality": "high",
            "feature-type": "dspsift",
            "matcher-type": "flann",
            "pc-quality": "high",
            "min-num-features": 20000,
            "use-hybrid-bundle-adjustment": True,
        },
        "meshing": {
            "mesh-octree-depth": 11,
            "mesh-size": 1_000_000,
        },
        "dem": {
            "dem-resolution": 5.0,
            "dem-decimation": 1,
        },
        "orthophoto": {
            "orthophoto-resolution": 5.0,
        },
    },

    "MEDIUM": {
        "dataset": {
            "gps-accuracy": 5.0,
        },
        "sfm": {
            "feature-quality": "medium",
            "feature-type": "dspsift",
            "matcher-type": "flann",
            "pc-quality": "medium",
            "min-num-features": 10000,
        },
        "meshing": {
            "mesh-octree-depth": 10,
            "mesh-size": 400_000,
        },
        "dem": {
            "dem-resolution": 10.0,
            "dem-decimation": 2,
        },
        "orthophoto": {
            "orthophoto-resolution": 10.0,
        },
    },

    "LOW": {
        "dataset": {
            "gps-accuracy": 10.0,
        },
        "sfm": {
            "feature-quality": "low",
            "feature-type": "orb",
            "matcher-type": "bruteforce",
            "pc-quality": "low",
            "min-num-features": 5000,
        },
        "filterpoints": {
            "fast-orthophoto": True,
        },
        "meshing": {
            "mesh-octree-depth": 9,
            "mesh-size": 200_000,
        },
        "dem": {
            "dem-resolution": 20.0,
            "dem-decimation": 4,
        },
        "orthophoto": {
            "orthophoto-resolution": 20.0,
        },
    },

    "ULTRA_LOW": {
        "dataset": {
            "gps-accuracy": 20.0,
        },
        "sfm": {
            "feature-quality": "lowest",
            "feature-type": "orb",
            "matcher-type": "bruteforce",
            "pc-quality": "lowest",
            "min-num-features": 2000,
            "use-hybrid-bundle-adjustment": True,
        },
        "filterpoints": {
            "fast-orthophoto": True,
            "pc-sample": 0.5,
        },
        "meshing": {
            "mesh-octree-depth": 8,
            "mesh-size": 100_000,
        },
        "dem": {
            "dem-resolution": 30.0,
            "dem-decimation": 6,
        },
        "orthophoto": {
            "orthophoto-resolution": 30.0,
            "orthophoto-png": True,
        },
        "report": {
            "skip-report": True,
        },
    },
}

@unique
class ODMQualityOption(StrEnum):
    ULTRA_HIGH = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    ULTRA_LOW = auto()

    @property
    def options(self) -> Dict[str, Dict[str, str]]:
        try:
            return ODM_QUALITY_OPTION_MAPPING[self.name]
        except KeyError:
            return []
    