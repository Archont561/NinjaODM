from ninja_extra import ModelService
from django.shortcuts import get_object_or_404

from app.api.models.task import ODMTask
from app.api.models.workspace import Workspace
from app.api.constants.odm import ODMTaskStatus


class TaskModelService(ModelService):
    def create(self, schema, **kwargs):
        data = schema.model_dump()

        # from permission check by controller to service so to not query 2nd time
        workspace = kwargs.get("workspace")

        task = self.model.objects.create(
            workspace=workspace,
            **data,
        )

        task.task_dir.mkdir(parents=True)
        return task

    def delete(self, instance, **kwargs):
        import shutil

        instance.delete()
        task_dir = instance.task_dir
        if task_dir.exists() and task_dir.is_dir():
            shutil.rmtree(task_dir, ignore_errors=True)

    def pause(self, instance: ODMTask, **kwargs):
        instance.status = ODMTaskStatus.PAUSING
        instance.save(update_fields=["status"])
        # → kill process, etc.

    def resume(self, instance: ODMTask, **kwargs):
        instance.status = ODMTaskStatus.RESUMING
        instance.save(update_fields=["status"])
        # → restart process

    def cancel(self, instance: ODMTask, **kwargs):
        instance.status = ODMTaskStatus.CANCELLING
        instance.save(update_fields=["status"])
        # → kill + cleanup
