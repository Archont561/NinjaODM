import pytest
import datetime
from django.db import IntegrityError, transaction
from django.contrib.gis.geos import Point


@pytest.mark.django_db
class TestGroundControlPoint:

    def test_gcp_creation_with_factory(self, ground_control_point_factory):
        gcp = ground_control_point_factory()
        # Basic field types
        assert isinstance(gcp.label, str)
        assert isinstance(gcp.image.name, str)
        assert isinstance(gcp.point, Point)
        assert isinstance(gcp.imgx, float)
        assert isinstance(gcp.imgy, float)
        assert isinstance(gcp.created_at, datetime.datetime)
        # Altitude must be positive
        assert gcp.alt > 0

    def test_gcp_label_random_string(self, ground_control_point_factory):
        gcp = ground_control_point_factory()
        assert isinstance(gcp.label, str)
        assert 8 <= len(gcp.label) <= 12  # Matches factory pystr length

    def test_gcp_properties(self, ground_control_point_factory):
        gcp = ground_control_point_factory()
        # lng, lat, alt match point coordinates
        assert gcp.lng == gcp.point.x
        assert gcp.lat == gcp.point.y
        assert gcp.alt == gcp.point.z

    def test_gcp_img_coordinates(self, ground_control_point_factory):
        gcp = ground_control_point_factory()
        # Image-space coordinates must be non-negative
        assert gcp.imgx >= 0
        assert gcp.imgy >= 0

    def test_gcp_to_odm_repr_format(self, ground_control_point_factory):
        gcp = ground_control_point_factory()
        repr_str = gcp.to_odm_repr()

        # Must include label and image name
        assert gcp.label in repr_str
        assert gcp.image.name in repr_str

        parts = repr_str.split()
        # Expected format:
        # lng lat alt imgx imgy image_name label
        assert len(parts) >= 7

        assert float(parts[0]) == pytest.approx(gcp.lng, rel=1e-6)
        assert float(parts[1]) == pytest.approx(gcp.lat, rel=1e-6)
        assert float(parts[2]) == pytest.approx(gcp.alt, rel=1e-3)
        assert float(parts[3]) == pytest.approx(gcp.imgx, rel=1e-3)
        assert float(parts[4]) == pytest.approx(gcp.imgy, rel=1e-3)

    def test_gcp_unique_label_constraint(self, ground_control_point_factory):
        gcp1 = ground_control_point_factory()
        # Creating another GCP with the same image & label should fail
        with pytest.raises(IntegrityError):
            ground_control_point_factory(
                image=gcp1.image,
                label=gcp1.label,
                point=Point(0, 0, 1)
            )

    def test_gcp_img_coordinates_must_be_non_negative(self, ground_control_point_factory):
        # Negative imgx
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ground_control_point_factory(
                    imgx=-1.0,
                    imgy=10.0,
                    point=Point(0, 0, 1),
                )

        # Negative imgy
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ground_control_point_factory(
                    imgx=10.0,
                    imgy=-1.0,
                    point=Point(0, 0, 1),
                )

    def test_gcp_point_is_3d(self, ground_control_point_factory):
        gcp = ground_control_point_factory()
        # Ensure point has 3 dimensions
        assert gcp.point.hasz
        assert gcp.point.z > 0
