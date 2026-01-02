import pytest
import datetime
from pathlib import Path
from PIL import Image as PILImage
from django.contrib.gis.geos import Point
from django.db import IntegrityError

from app.api.models.gcp import GroundControlPoint


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

    def test_image_creation(self, image_factory):
        image = image_factory(name="example.png")
        assert image.name == "example.png"
        assert not image.is_thumbnail
        assert image.workspace is not None
        assert image.image_file  # File exists in storage
        assert isinstance(image.created_at, datetime.datetime)

    def test_make_thumbnail_creates_thumbnail(self, image_factory):
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

    def test_make_thumbnail_on_thumbnail_returns_self(self, image_factory):
        thumb = image_factory(is_thumbnail=True)
        result = thumb.make_thumbnail()
        assert result.image_file == thumb.image_file
        assert result == thumb


@pytest.mark.django_db
class TestGroundControlPoint:

    def test_gcp_creation_with_factory(self, gcp_factory):
        gcp = gcp_factory()
        # Basic field types
        assert isinstance(gcp.label, str)
        assert isinstance(gcp.image.name, str)
        assert isinstance(gcp.point, Point)
        # Altitude must be positive
        assert gcp.point.z > 0

    def test_gcp_label_random_string(self, gcp_factory):
        gcp = gcp_factory()
        assert isinstance(gcp.label, str)
        assert 8 <= len(gcp.label) <= 12  # Matches factory pystr length

    def test_gcp_properties(self, gcp_factory):
        gcp = gcp_factory()
        # lng, lat, alt match point coordinates
        assert gcp.lng == gcp.point.x
        assert gcp.lat == gcp.point.y
        assert gcp.alt == gcp.point.z

    def test_gcp_to_odm_repr_format(self, gcp_factory):
        gcp = gcp_factory()
        repr_str = gcp.to_odm_repr()
        # Must include label and image name
        assert gcp.label in repr_str
        assert gcp.image.name in repr_str
        # First three parts must be lng, lat, alt as floats
        parts = repr_str.split()
        assert len(parts) >= 5
        assert float(parts[0]) == pytest.approx(gcp.lng, rel=1e-6)
        assert float(parts[1]) == pytest.approx(gcp.lat, rel=1e-6)
        assert float(parts[2]) == pytest.approx(gcp.alt, rel=1e-3)

    def test_gcp_unique_label_constraint(self, gcp_factory):
        gcp1 = gcp_factory()
        from django.db import IntegrityError
        # Creating another GCP with the same image & label should fail
        with pytest.raises(IntegrityError):
            GroundControlPoint.objects.create(
                image=gcp1.image,
                label=gcp1.label,
                point=Point(0, 0, 1)
            )

    def test_gcp_point_is_3d(self, gcp_factory):
        gcp = gcp_factory()
        # Ensure point has 3 dimensions
        assert gcp.point.hasz
        assert gcp.point.z > 0