from django.db import models
from pathlib import Path
from PIL import Image as PILImage
import io
from django.core.files.base import ContentFile
from app.api.models.workspace import Workspace
from app.config.settings.main import get_settings
from app.api.models.mixins import UUIDPrimaryKeyModelMixin, TimeStampedModelMixin


def dynamic_upload_path(instance, filename):
    base_dir = get_settings().THUMBNAILS_DIR_NAME if instance.is_thumbnail else get_settings().IMAGES_DIR_NAME
    return str(Path(base_dir) / str(instance.workspace.uuid) / filename)


class Image(UUIDPrimaryKeyModelMixin, TimeStampedModelMixin, models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="images"
    )
    name = models.CharField(max_length=50)
    image_file = models.ImageField(upload_to=dynamic_upload_path)
    is_thumbnail = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name", "is_thumbnail"],
                name="unique_image_per_workspace_per_type",
            )
        ]

    def __str__(self):
        kind = "thumb" if self.is_thumbnail else "image"
        return f"{self.workspace.name}: {self.name} ({kind})"

    def make_thumbnail(self, size=(256, 256)) -> "Image":
        """
        Create a thumbnail from this image.
        Returns a new Image object with is_thumbnail=True.
        """
        if self.is_thumbnail:
            return self

        thumb = Image.objects.create(
            workspace=self.workspace,
            name=self.name,
            is_thumbnail=True,
        )

        # Open original image
        with PILImage.open(self.image_file.path) as im:
            im.thumbnail(size)
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            thumb.image_file.save(self.name, ContentFile(buf.getvalue()), save=True)

        return thumb
