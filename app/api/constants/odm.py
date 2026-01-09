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
