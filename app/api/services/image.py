from pathlib import Path
from ninja_extra import ModelService


class ImageModelService(ModelService):
    def delete(self, instance, **kwargs):
        instance.delete()
        file_path = Path(instance.image_file.path)
        if file_path.exists():
            file_path.unlink()
    