from __future__ import annotations
from pathlib import Path
from enum import auto, unique, Enum, StrEnum
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
    def stage_results(self) -> List[ODMTaskResultType]:
        try:
            return ODM_PROCESSING_STAGE_RESULTS_MAPPING[self.name]
        except KeyError:
            return []
