from typing import List
from ninja_extra import ModelService
from ninja.files import UploadedFile

from app.api.models.image import Image
from app.api.sse import emit_event


class WorkspaceModelService(ModelService):
    def create(self, schema, **kwargs):
        instance = super().create(schema, **kwargs)
        emit_event(
            instance.user_id,
            "workspace:created",
            {"uuid": str(instance.uuid), "name": instance.name},
        )
        return instance

    def update(self, instance, schema, **kwargs):
        update_instance = super().update(instance, schema, **kwargs)
        emit_event(
            update_instance.user_id,
            "workspace:updated",
            {"uuid": str(instance.uuid), "name": instance.name},
        )
        return update_instance

    def delete(self, instance):
        payload = {"uuid": str(instance.uuid), "name": instance.name}
        instance.delete()
        emit_event(instance.user_id, "workspace:deleted", payload)

    def save_images(self, instance, image_files: List[UploadedFile]):
        images = []
        for image_file in image_files:
            image = Image.objects.create(workspace=instance, image_file=image_file)
            image.make_thumbnail()
            images.append(image)

        emit_event(
            instance.user_id,
            "workspace:images-uploaded",
            {
                "uuid": str(instance.uuid),
                "uploaded": len(images),
            },
        )
        return images
