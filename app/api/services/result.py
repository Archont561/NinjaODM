from pathlib import Path
from ninja_extra import ModelService

from app.api.sse import emit_event


class ResultModelService(ModelService):
    def delete(self, instance, **kwargs):
        payload = {"uuid": str(instance.uuid), "result_type": instance.odm_result_type.label}
        instance.delete()
        file_path = Path(instance.file.path)
        if file_path.exists():
            file_path.unlink()

        emit_event(instance.workspace.user_id, "task-result:deleted", payload)

