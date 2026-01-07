from pathlib import Path
from ninja_extra import ModelService

from app.api.sse import emit_event


class ImageModelService(ModelService):
    def delete(self, instance, **kwargs):
        payload = {"uuid": str(instance.uuid), "name": instance.name}
        instance.delete()
        file_path = Path(instance.image_file.path)
        if file_path.exists():
            file_path.unlink()

        emit_event(instance.workspace.user_id, "image:deleted", payload)
