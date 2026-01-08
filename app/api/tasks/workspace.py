import shutil
from typing import List
from uuid import UUID
from celery import shared_task
from pathlib import Path

from app.api.models.workspace import Workspace
from app.api.models.image import Image


@shared_task
def on_workspace_images_uploaded(image_uuids: List[UUID]):
    images = Image.objects.filter(uuid__in=image_uuids)
    for image in images:
        image.make_thumbnail()
