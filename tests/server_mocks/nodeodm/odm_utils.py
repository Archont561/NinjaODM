import time
import io
import zipfile
import factory
from faker import Faker
from enum import IntEnum
from uuid import uuid4
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

fake = Faker()

# ==========================
# Constants
# ==========================


class MockTaskStatus(IntEnum):
    QUEUED = 10
    RUNNING = 20
    FAILED = 30
    COMPLETED = 40
    CANCELED = 50


# ==========================
# Models
# ==========================


@dataclass
class MockTaskStatusInfo:
    code: int = MockTaskStatus.QUEUED


@dataclass
class MockODMTask:
    """Data container for Task info. JSON-serializable."""

    uuid: str
    name: str
    dateCreated: int

    processingTime: int = 0
    imagesCount: int = 0
    progress: float = 0.0

    status: MockTaskStatusInfo = field(
        default_factory=lambda: MockTaskStatusInfo(code=MockTaskStatus.QUEUED)
    )
    options: List[Dict[str, Any]] = field(default_factory=list)
    output: List[str] = field(default_factory=list)

    def add_log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.output.append(f"[{timestamp}] {message}")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    # --------------------------
    # Model Actions (State)
    # --------------------------

    def commit(self) -> None:
        """Transition from Init/Queued to Running."""
        self.status.code = MockTaskStatus.RUNNING
        self.progress = 15.0
        self.add_log("Task committed. Moving to processing queue.")

    def cancel(self) -> None:
        """Force task into Canceled state."""
        self.status.code = MockTaskStatus.CANCELED
        self.add_log("Task canceled by administrative request.")

    def restart(self, options: Optional[List[Dict[str, Any]]] = None) -> None:
        """Reset the task to its initial state, optionally updating options."""
        if options is not None:
            self.options = options

        self.status.code = MockTaskStatus.QUEUED
        self.progress = 0.0
        self.processingTime = 0
        self.output.clear()
        self.add_log("Task restarted. Options updated. Logs cleared.")

    def complete(self) -> None:
        """Mark as successfully finished."""
        self.status.code = MockTaskStatus.COMPLETED
        self.progress = 100.0
        self.add_log("Task finished successfully.")

    def fail(self, error_msg: str = "Internal error") -> None:
        """Mark as failed."""
        self.status.code = MockTaskStatus.FAILED
        self.add_log(f"Task failed: {error_msg}")


# ==========================
# Factories
# ==========================


class MockODMTaskFactory(factory.Factory):
    class Meta:
        model = MockODMTask

    uuid = factory.LazyFunction(lambda: str(uuid4()))
    name = factory.Faker("catch_phrase")
    dateCreated = factory.LazyFunction(lambda: int(time.time() * 1000))

    processingTime = 0
    imagesCount = 0
    progress = 0.0
    status = factory.LazyFunction(
        lambda: MockTaskStatusInfo(code=MockTaskStatus.QUEUED)
    )
    options = factory.List([])
    output = factory.List([])


class MockODMAssetFactory:
    """Generates valid binary files/zips for downloads."""

    @staticmethod
    def create_zip() -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("orthophoto.tif", b"fake_tiff_data")
            zf.writestr("log.txt", b"processing complete")
        return buf.getvalue()


# ==========================
# Business Logic Manager
# ==========================


class MockODMTaskManager:
    def __init__(self):
        self.tasks: Dict[str, MockODMTask] = {}

    # --------------------------
    # Queries
    # --------------------------

    def get_task(self, uuid: str) -> Optional[MockODMTask]:
        return self.tasks.get(uuid)

    def list_uuids(self) -> List[str]:
        return list(self.tasks.keys())

    def get_queue_count(self) -> int:
        return sum(
            1
            for task in self.tasks.values()
            if task.status.code < MockTaskStatus.COMPLETED
        )

    def create_init(
        self, uuid: str, name: Optional[str], options: List[Dict[str, Any]]
    ) -> MockODMTask:
        task = MockODMTaskFactory(
            uuid=uuid,
            name=name or "New Task",
            options=options,
        )
        task.add_log(f"Task created. UUID: {uuid}")
        self.tasks[uuid] = task
        return task

    def create_shortcut(self, uuid: str, name: Optional[str]) -> MockODMTask:
        uuid = self.create_init(uuid, name, [])
        self.commit(uuid)  # Start immediately
        return task

    def remove(self, uuid: str) -> bool:
        return self.tasks.pop(uuid, None) is not None

    def set_status(self, uuid: str, status_name: str) -> None:
        """Helper for tests to force a specific status."""
        if task := self.get_task(uuid):
            if status_name == "COMPLETED":
                task.complete()
            elif status_name == "CANCELED":
                task.cancel()
            elif status_name == "FAILED":
                task.fail()
            elif status_name == "RUNNING":
                task.commit()
