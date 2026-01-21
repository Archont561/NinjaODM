from typing import TypeVar, Generic, Union, Literal
from ninja import Schema
from pydantic import BaseModel

from .workspace import (
    WorkspaceCreatedSSEData,
    WorkspaceUpdatedSSEData,
    WorkspaceDeletedSSEData,
    WorkspaceImagesUploadedSSEData,
)
from .image import ImageDeletedSSEData
from .result import ResultDeletedSSEData, ResultCreatedSSEData
from .task import (
    TaskCreatedSSEData,
    TaskUpdatedSSEData,
    TaskDeletedSSEData,
    TaskPausedSSEData,
    TaskResumedSSEData,
    TaskCancelledSSEData,
    TaskNextStageSSEData,
    TaskStartedSSEData,
    TaskCompletedSSEData,
    TaskFailedSSEData,
)
from .gcp import GPCCreatedSSEData, GCPUpdatedSSEData, GCPDeletedSSEData

E = TypeVar("E", bound=str)
T = TypeVar("T", bound=Schema)


class SSEWrapper(BaseModel, Generic[E, T]):
    event: E
    data: T


class HeartbeatEvent(Schema):
    event: Literal["heartbeat"] = "heartbeat"


_EVENTS = {
    "workspace:created": WorkspaceCreatedSSEData,
    "workspace:updated": WorkspaceUpdatedSSEData,
    "workspace:deleted": WorkspaceDeletedSSEData,
    "workspace:images-uploaded": WorkspaceImagesUploadedSSEData,
    "image:deleted": ImageDeletedSSEData,
    "task-result:deleted": ResultDeletedSSEData,
    "task-result:created": ResultCreatedSSEData,
    "task:created": TaskCreatedSSEData,
    "task:updated": TaskUpdatedSSEData,
    "task:deleted": TaskDeletedSSEData,
    "task:paused": TaskPausedSSEData,
    "task:resumed": TaskResumedSSEData,
    "task:cancelled": TaskCancelledSSEData,
    "task:next-stage": TaskNextStageSSEData,
    "task:started": TaskStartedSSEData,
    "task:completed": TaskCompletedSSEData,
    "task:failed": TaskFailedSSEData,
    "gcp:created": GPCCreatedSSEData,
    "gcp:updated": GCPUpdatedSSEData,
    "gcp:deleted": GCPDeletedSSEData,
}

ServerSideEvent = Union[
    HeartbeatEvent,
    *(
        SSEWrapper[Literal[event_name], payload]
        for event_name, payload in _EVENTS.items()
    ),
]
