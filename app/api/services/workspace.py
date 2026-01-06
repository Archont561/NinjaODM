import json
from typing import List
from ninja_extra import ModelService
from ninja.files import UploadedFile

from app.api.models.image import Image
from app.api.sse import emit_event


class WorkspaceModelService(ModelService):
    def create(self, schema, **kwargs):
        instance = super().create(schema, **kwargs)
        emit_event(instance.user_id, "workspace:created", {
            "uuid": str(instance.uuid),
            "name": instance.name
        })
        return instance
    
    def save_images(self, instance, image_files: List[UploadedFile]):
        images = []
        for image_file in image_files:
            image = Image.objects.create(workspace=instance, image_file=image_file)
            image.make_thumbnail()
            images.append(image)
        return images
            