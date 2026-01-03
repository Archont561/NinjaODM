import pytest
import datetime
from pathlib import Path
from PIL import Image as PILImage
from django.db import IntegrityError, transaction
from django.contrib.gis.geos import Point
from django.core.files import File

from app.api.constants.odm import ODMTaskStatus, ODMProcessingStage, ODMTaskResultType


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


@pytest.mark.django_db
class TestODMTask:
    def test_task_creation(self, odm_task_factory):
        """
        Test that an ODMTask can be created with specific attributes.
        """
        task = odm_task_factory(status=ODMTaskStatus.RUNNING.value, step=ODMProcessingStage.MVS.value)
        assert task.odm_status == ODMTaskStatus.RUNNING
        assert task.odm_step == ODMProcessingStage.MVS
        assert task.uuid is not None
        assert isinstance(task.created_at, datetime.datetime)
        assert task.workspace.uuid is not None
        
    def test_task_dir_property(self, odm_task_factory, tmp_path, settings):
        """
        Test that task_dir returns the correct path under TASKS_DIR.
        """
        setattr(settings, "TASKS_DIR", tmp_path)
        task = odm_task_factory()
        expected_path = tmp_path / str(task.workspace.uuid) / str(task.uuid)
        assert task.task_dir == expected_path

    def test_get_current_step_options_returns_dict(self, odm_task_factory):
        """
        Test that get_current_step_options returns a dict even if empty.
        """
        task = odm_task_factory(options={ODMProcessingStage.DATASET.value: {"param": 123}})
        options = task.get_current_step_options()
        assert isinstance(options, dict)
        if task.odm_step == ODMProcessingStage.DATASET:
            assert options.get("param") == 123

    
@pytest.mark.django_db
class TestODMTaskResult:
    def test_task_result_creation(self, odm_task_result_factory):
        """
        Test that an ODMTaskResult can be created with specific attributes.
        """
        task_result = odm_task_result_factory(result_type=ODMTaskResultType.DTM.value)
        assert task_result.odm_result_type == ODMTaskResultType.DTM
        assert task_result.uuid is not None
        assert isinstance(task_result.created_at, datetime.datetime)
        assert task_result.workspace.uuid is not None
        
    def test_file_upload(temp_media, tmp_path, odm_task_result_factory, settings):
        temp_file = tmp_path / "test_file.txt"
        temp_file.write_text("This is a test file")

        with open(temp_file, "rb") as f:
            task_result = odm_task_result_factory(
                result_type=ODMTaskResultType.MESH.value, 
                file=File(f, name=temp_file.name)
            )

        assert task_result.file.name is not None
        uploaded_file_path = Path(task_result.file.path)
        assert uploaded_file_path.exists()
        assert uploaded_file_path.read_text() == "This is a test file"
        expected_path = Path(getattr(settings, "MEDIA_ROOT")) / getattr(settings, "RESULTS_DIR_NAME") / str(task_result.workspace.uuid)
        assert uploaded_file_path.parent 
