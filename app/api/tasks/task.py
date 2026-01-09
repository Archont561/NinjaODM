from uuid import UUID
from celery import shared_task
from pathlib import Path

from app.api.models.task import ODMTask


@shared_task
def on_task_create(odm_task_uuid: UUID):
    odm_task = ODMTask.objects.get(uuid=odm_task_uuid)
    odm_task.task_dir.mkdir(parents=True) 


@shared_task
def on_task_pause(odm_task_uuid: UUID):
    odm_task = ODMTask.objects.get(uuid=odm_task_uuid)


@shared_task
def on_task_resume(odm_task_uuid: UUID):
    odm_task = ODMTask.objects.get(uuid=odm_task_uuid)


@shared_task
def on_task_cancel(odm_task_uuid: UUID):
    odm_task = ODMTask.objects.get(uuid=odm_task_uuid)
    

@shared_task
def on_task_nodeodm_webhook(odm_task_uuid: UUID):
    odm_task = ODMTask.objects.get(uuid=odm_task_uuid)

@shared_task
def on_task_finish(odm_task_uuid: UUID):
    odm_task = ODMTask.objects.get(uuid=odm_task_uuid)
    