from celery import shared_task

from app.api.models.task import ODMTask


@shared_task
def on_odm_task_creation(odm_task_uuid: ODMTask):
    odm_task = ODMTask.objects.get(uuid=odm_task_uuid)
    print("Some postprocessing after ODMTask creation!")   
    odm_task.task_dir.mkdir(parents=True) 
