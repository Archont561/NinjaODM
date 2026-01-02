import pytest
import datetime
from pathlib import Path
from PIL import Image as PILImage


@pytest.mark.django_db
class TestWorkspace:
    def test_workspace_creation(self, workspace_factory):
        workspace = workspace_factory(name="Project Alpha")
        assert workspace.name == "Project Alpha"
        assert isinstance(workspace.uuid, str) or workspace.uuid is not None
        assert isinstance(workspace.created_at, datetime.datetime) or workspace.uuid is not None

    def test_workspace_creation_no_name_provided(self, workspace_factory):
        workspace = workspace_factory()
        assert isinstance(workspace.name, str)


@pytest.mark.django_db
class TestImage:

    def test_image_creation(self, image_factory, temp_media):
        image = image_factory(name="example.png")
        assert image.name == "example.png"
        assert not image.is_thumbnail
        assert image.workspace is not None
        assert image.image_file  # File exists in storage
        assert isinstance(image.created_at, datetime.datetime)

    def test_make_thumbnail_creates_thumbnail(self, image_factory, temp_media):
        original = image_factory()
        thumb = original.make_thumbnail(size=(128, 128))

        # Check thumbnail object
        assert thumb.is_thumbnail
        assert thumb.workspace == original.workspace
        assert thumb.name == original.name
        assert thumb.image_file  # File exists in storage

        # Check thumbnail dimensions
        with PILImage.open(thumb.image_file.path) as im:
            assert im.width <= 128
            assert im.height <= 128

    def test_make_thumbnail_on_thumbnail_returns_self(self, image_factory, temp_media):
        thumb = image_factory(is_thumbnail=True)
        result = thumb.make_thumbnail()
        assert result.image_file == thumb.image_file
        assert result == thumb