from ninja_extra import ModelService
from django.db import transaction

from app.api.constants.odm import ODMTaskStatus
from app.api.sse import emit_event
from app.api.tasks.task import (
    on_task_create,
    on_task_pause,
    on_task_resume,
    on_task_cancel,
    on_task_nodeodm_webhook,
    on_task_finish,
    on_task_failure,
)


class TaskModelService(ModelService):
    def create(self, schema, **kwargs):
        data = schema.model_dump()
        workspace = kwargs.get("workspace")
        quality = data.pop("quality")
        
        with transaction.atomic():
            instance = self.model.objects.create(
                workspace=workspace,
                options=quality.options,
                **data,
            )

        on_task_create.delay(instance.uuid)
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
        with transaction.atomic():
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
        payload = {
            "uuid": str(instance.uuid),
            "status": instance.odm_status,
            "step": instance.odm_step,
        }
        user_id = instance.workspace.user_id
        instance.delete()
        emit_event(user_id, "task:deleted", payload)

    def action(self, action, instance, update_schema):
        match action:
            case "pause":
                updated_instance = self.update(
                    instance, update_schema, status=ODMTaskStatus.PAUSING
                )
                on_task_pause.delay(updated_instance.uuid)
            case "resume":
                updated_instance = self.update(
                    instance, update_schema, status=ODMTaskStatus.RESUMING
                )
                on_task_resume.delay(updated_instance.uuid)
            case "cancel":
                updated_instance = self.update(
                    instance, update_schema, status=ODMTaskStatus.CANCELLING
                )
                on_task_cancel.delay(updated_instance.uuid)
            case _:
                raise ValueError(f"{self.__class__.__name__} has no '{action}' action!")
        
        return updated_instance
 
    def proceed_next_task_step(self, instance, update_schema):
        odm_processing_stage = instance.odm_step.next_stage
        if not odm_processing_stage:
            updated_instance = self.update(
                instance,
                update_schema,
                status=ODMTaskStatus.FINISHING,
            )
            on_task_finish.delay(updated_instance.uuid)
            return

        updated_instance = self.update(
            instance, 
            update_schema, 
            status=ODMTaskStatus.QUEUED,
            step=odm_processing_stage
        )
        on_task_nodeodm_webhook.delay(updated_instance.uuid)

    def handle_failure(self, instance):
        on_task_failure.delay(updated_instance.uuid)
