from ninja_extra import ModelService
from django.db import transaction

from app.api.constants.odm import ODMTaskStatus
from app.api.sse import emit_event
from app.api.tasks.task import on_odm_task_creation


class TaskModelService(ModelService):
    def create(self, schema, **kwargs):
        data = schema.model_dump()
        workspace = kwargs.get("workspace")
        
        with transaction.atomic():
            instance = self.model.objects.create(
                workspace=workspace,
                **data,
            )

        on_odm_task_creation.delay(instance.uuid)
        emit_event(
            instance.workspace.user_id,
            "task:created",
            {
                "uuid": str(instance.uuid),
                "status": instance.odm_status,
                "step": instance.odm_step,
            },
        )
        return instance

    def update(self, instance, schema, **kwargs):
        update_instance = super().update(instance, schema, **kwargs)
        emit_event(
            update_instance.workspace.user_id,
            "task:updated",
            {
                "uuid": str(update_instance.uuid),
                "status": update_instance.odm_status,
                "step": update_instance.odm_step,
            },
        )
        return update_instance

    def delete(self, instance, **kwargs):
        import shutil

        payload = {
            "uuid": str(instance.uuid),
            "status": instance.odm_status,
            "step": instance.odm_step,
        }
        instance.delete()
        task_dir = instance.task_dir
        if task_dir.exists() and task_dir.is_dir():
            shutil.rmtree(task_dir, ignore_errors=True)

        emit_event(instance.workspace.user_id, "task:deleted", payload)

    def action(self, action, instance, update_schema):
        match action:
            case "pause":
                return self.update(
                    instance, update_schema, status=ODMTaskStatus.PAUSING
                )
            case "resume":
                return self.update(
                    instance, update_schema, status=ODMTaskStatus.RESUMING
                )
            case "cancel":
                return self.update(
                    instance, update_schema, status=ODMTaskStatus.CANCELLING
                )
        raise ValueError(f"{self.__class__.__name__} has no '{action}' action!")
