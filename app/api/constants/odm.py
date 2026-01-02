from __future__ import annotations
from enum import IntEnum, auto, unique
from typing import Dict, Optional, Type

from pydantic import BaseModel, Field


class ChoicesMixin:
    """
    Mixin that adds a Django-style `choices()` method to any Enum subclass.
    """

    @property
    def label(self) -> str:
        """
        Human‑readable label for this enum member.

        - For StrEnum: based on the string value
        - For IntEnum/Enum: based on the member name
        """
        source = self.value if isinstance(self.value, str) else self.name
        return source.replace("_", " ").title()

    @classmethod
    def choices(cls):
        """
        Return Django-style choices: list of (value, label) tuples.
        """
        return [(member.value, member.label) for member in cls]


@unique
class ODMTaskStatus(ChoicesMixin, IntEnum):
    # Initial States
    QUEUED = auto()  # Task is waiting in queue

    # Active States
    RUNNING = auto()  # Task is currently processing
    STOPPING = auto() # Task is being stopped
    PAUSED = auto()  # Task is temporarily paused (can resume)
    CANCELLING = auto()

    # Terminal States - Success
    COMPLETED = auto()  # Task finished successfully

    # Terminal States - Failure
    FAILED = auto()  # Task failed due to error
    CANCELLED = auto()  # Task was cancelled by user
    TIMEOUT = auto()  # Task exceeded time limit

    # Special States
    RESUMING = auto()  # Task is resuming from pause/checkpoint


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
