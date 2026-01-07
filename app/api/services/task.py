from ninja_extra import ModelService

from app.api.constants.odm import ODMTaskStatus


class TaskModelService(ModelService):
    def create(self, schema, **kwargs):
        data = schema.model_dump()
        workspace = kwargs.get("workspace")
        instance = self.model.objects.create(
            workspace=workspace,
            **data,
        )
        instance.task_dir.mkdir(parents=True)
        return instance

    def delete(self, instance, **kwargs):
        import shutil

        instance.delete()
        task_dir = instance.task_dir
        if task_dir.exists() and task_dir.is_dir():
            shutil.rmtree(task_dir, ignore_errors=True)

    def action(self, action, instance, update_schema):
        match action:
            case "pause":
                return self.update(instance, update_schema, status=ODMTaskStatus.PAUSING)
            case "resume":
                return self.update(instance, update_schema, status=ODMTaskStatus.RESUMING)
            case "cancel":
                return self.update(instance, update_schema, status=ODMTaskStatus.CANCELLING)
        raise ValueError(f"{self.__class__.__name__} has no '{action}' action!")
    