import pytest
import datetime
from PIL import Image as PILImage


@pytest.mark.django_db
class TestImage:

    def test_image_creation(self, image_factory):
        image = image_factory(name="example.png")
        assert image.name == "example.png"
        assert not image.is_thumbnail
        assert image.workspace is not None
        assert isinstance(image.created_at, datetime.datetime)

    def test_make_thumbnail_creates_thumbnail(self, image_factory, temp_image_file):
        original = image_factory(image_file=temp_image_file)
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

    def test_make_thumbnail_on_thumbnail_returns_self(self, image_factory, temp_image_file):
        thumb = image_factory(is_thumbnail=True, image_file=temp_image_file)
        result = thumb.make_thumbnail()
        assert result.image_file == thumb.image_file
        assert result == thumb
