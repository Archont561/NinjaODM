from typing import Optional, Callable
from uuid import UUID
from celery import shared_task
from pathlib import Path
from django.core.files import File
from django.db import transaction
from pyodm.exceptions import OdmError, NodeResponseError
from loguru import logger
from datetime import datetime

from app.api.models.task import ODMTask
from app.api.models.image import Image
from app.api.models.result import ODMTaskResult
from app.api.sse import emit_event
from app.api.constants.odm import ODMTaskStatus, ODMTaskResultType
from app.api.constants.odm_client import NodeODMClient


def save_task_status(odm_task: ODMTask, status: ODMTaskStatus):
    with transaction.atomic():
        odm_task.status = status.value
        odm_task.save(update_fields=["status"])


def emit_task_event(
    odm_task: ODMTask,
    event_type: str,
    error: Optional[str] = None,
    **payload,
):
    data = {"uuid": str(odm_task.uuid)}
    if error:
        data["error"] = error
    else:
        data.update(payload)
    emit_event(odm_task.workspace.user_id, event_type, data)


def handle_task_failure(
    odm_task: ODMTask,
    error: Exception,
    is_node_error: bool = False,
):
    if is_node_error:
        error_message = "Cannot connect to node service"
        logger.error(f"Task {odm_task.uuid} failed due to node error: {error}")
    else:
        error_message = f"Unexpected error: {error}"
        logger.exception(f"Task {odm_task.uuid} failed unexpectedly")

    save_task_status(odm_task, ODMTaskStatus.FAILED)
    emit_task_event(odm_task, "task:failed", error=error_message)


def execute_task_operation(
    odm_task_uuid: UUID,
    operation: Callable[[ODMTask], None],
    success_status: ODMTaskStatus,
    success_event: str,
):
    odm_task = None
    try:
        odm_task = ODMTask.objects.get(uuid=odm_task_uuid)
        operation(odm_task)
        save_task_status(odm_task, success_status)
        emit_task_event(odm_task, success_event)

    except ODMTask.DoesNotExist:
        logger.error(f"Task {odm_task_uuid} not found")
    except OdmError as e:
        if odm_task:
            handle_task_failure(odm_task, e, is_node_error=True)
        else:
            logger.error(f"Node error for task {odm_task_uuid}: {e}")
    except Exception as e:
        if odm_task:
            handle_task_failure(odm_task, e)
        else:
            logger.exception(f"Unexpected error for task {odm_task_uuid}")


def save_task_stage_result(
    odm_task: ODMTask, odm_task_result_file_path: Path, stage_result: ODMTaskResultType
):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{odm_task_result_file_path.stem}_{timestamp}{odm_task_result_file_path.suffix}"

    with transaction.atomic(), open(odm_task_result_file_path, "rb") as f:
        task_result = ODMTaskResult.objects.create(
            result_type=stage_result,
            workspace=odm_task.workspace,
            file=File(f, name=new_filename),
        )

    emit_event(
        task_result.workspace.user_id,
        "task-result:created",
        {
            "uuid": str(task_result.uuid),
            "workspace_name": task_result.workspace.name,
        },
    )


@shared_task
def on_task_create(odm_task_uuid: UUID):
    def _create(odm_task: ODMTask):
        images = Image.objects.filter(workspace=odm_task.workspace, is_thumbnail=False)
        image_paths = [str(img.image_file.path) for img in images]
        node = NodeODMClient.for_task(odm_task.uuid)
        options = {
            **odm_task.get_current_step_options(),
            "rerun-from": odm_task.step,
            "end-with": odm_task.step,
        }
        node.create_task(files=image_paths, options=options)

    execute_task_operation(
        odm_task_uuid,
        _create,
        ODMTaskStatus.RUNNING,
        "task:started",
    )


@shared_task
def on_task_pause(odm_task_uuid: UUID):
    def _pause(odm_task: ODMTask):
        node = NodeODMClient.for_task(odm_task.uuid)
        task = node.get_task(str(odm_task.uuid))

        if not task.cancel():
            raise NodeResponseError("Failed to pause task")

    execute_task_operation(
        odm_task_uuid,
        _pause,
        ODMTaskStatus.PAUSED,
        "task:paused",
    )


@shared_task
def on_task_resume(odm_task_uuid: UUID):
    def _resume(odm_task: ODMTask):
        node = NodeODMClient.for_task(odm_task.uuid)
        task = node.get_task(str(odm_task.uuid))

        options = {
            **odm_task.get_current_step_options(),
            "rerun-from": odm_task.step,
            "end-with": odm_task.step,
        }

        if not task.restart(options=options):
            raise NodeResponseError("Failed to resume task")

    execute_task_operation(
        odm_task_uuid,
        _resume,
        ODMTaskStatus.RUNNING,
        "task:resumed",
    )


@shared_task
def on_task_cancel(odm_task_uuid: UUID):
    def _cancel(odm_task: ODMTask):
        node = NodeODMClient.for_task(odm_task.uuid)
        task = node.get_task(str(odm_task.uuid))
        if not task.remove():
            raise NodeResponseError("Failed to cancel task")

    execute_task_operation(
        odm_task_uuid,
        _cancel,
        ODMTaskStatus.CANCELLED,
        "task:cancelled",
    )


@shared_task
def on_task_nodeodm_webhook(odm_task_uuid: UUID):
    def _next_stage(odm_task: ODMTask):
        node = NodeODMClient.for_task(odm_task.uuid)
        task = node.get_task(str(odm_task.uuid))

        options = {
            **odm_task.get_current_step_options(),
            "rerun-from": odm_task.step,
            "end-with": odm_task.step,
        }

        for stage_result in odm_task.odm_step.previous_stage.stage_results:
            result_file_path = odm_task.task_dir / stage_result.relative_path
            if not result_file_path.exists():
                continue
            save_task_stage_result(odm_task, result_file_path, stage_result)

        if not task.restart(options=options):
            raise NodeResponseError("Failed to start new stage task")

    execute_task_operation(
        odm_task_uuid,
        _next_stage,
        ODMTaskStatus.RUNNING,
        "task:next-stage",
    )


@shared_task
def on_task_finish(odm_task_uuid: UUID):
    def _finish(odm_task: ODMTask):
        node = NodeODMClient.for_task(odm_task.uuid)
        task = node.get_task(str(odm_task.uuid))

        if not task.remove():
            raise NodeResponseError("Failed to cleanup task artifacts on nodeodm")

    execute_task_operation(
        odm_task_uuid,
        _finish,
        ODMTaskStatus.COMPLETED,
        "task:completed",
    )


@shared_task
def on_task_failure(odm_task_uuid: UUID):
    def _failed(odm_task: ODMTask):
        node = NodeODMClient.for_task(odm_task.uuid)
        task = node.get_task(str(odm_task.uuid))

        if not task.remove():
            raise NodeResponseError("Failed to cleanup task artifacts on nodeodm")

    execute_task_operation(
        odm_task_uuid,
        _failed,
        ODMTaskStatus.FAILED,
        "task:failed",
    )
