from __future__ import annotations
from enum import IntEnum, auto, unique, Enum
from typing import (
    Optional,
    FrozenSet,
    List,
    Tuple,
    Union,
)


class ChoicesMixin(Enum):
    @property
    def label(self) -> str:
        source = self.value if isinstance(self.value, str) else self.name
        return source.replace("_", " ").title()

    @classmethod
    def choices(cls) -> List[Tuple[Union[int, str], str]]:
        return [(member.value, member.label) for member in cls]


@unique
class ODMTaskStatus(ChoicesMixin, IntEnum):
    # Initial States
    QUEUED = auto()

    # Active States
    RUNNING = auto()
    PAUSING = auto()
    PAUSED = auto()
    RESUMING = auto()
    CANCELLING = auto()

    # Terminal States - Success
    COMPLETED = auto()

    # Terminal States - Failure
    FAILED = auto()
    CANCELLED = auto()
    TIMEOUT = auto()

    @classmethod
    def terminal_states(cls) -> FrozenSet[ODMTaskStatus]:
        return frozenset(
            {
                cls.COMPLETED,
                cls.FAILED,
                cls.CANCELLED,
                cls.TIMEOUT,
            }
        )

    @classmethod
    def non_terminal_states(cls) -> FrozenSet[ODMTaskStatus]:
        return frozenset(set(cls) - cls.terminal_states())

    def is_terminal(self) -> bool:
        return self in self.terminal_states()


class ODMProcessingStage(ChoicesMixin, IntEnum):
    DATASET = auto()
    SPLITTING = auto()
    MERGING = auto()
    SFM = auto()
    MVS = auto()
    FILTER_POINTS = auto()
    MESHING = auto()
    TEXTURING = auto()
    GEOREFERENCING = auto()
    DEM_PROCESSING = auto()
    ORTHOPHOTO_PROCESSING = auto()
    REPORTING = auto()
    POSTPROCESSING = auto()

    def next_stage(self, stage: ODMProcessingStage) -> Optional[ODMProcessingStage]:
        try:
            return stage.__class__(stage.value + 1)
        except ValueError:
            return None


@unique
class ODMTaskResultType(ChoicesMixin, IntEnum):
    DEM = auto()
    DSM = auto()
    DTM = auto()
    POINT_CLOUD = auto()
    MESH = auto()
    ORTHOMOSAIC = auto()
    REPORT = auto()
