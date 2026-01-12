import pytest
from uuid import uuid4
from unittest.mock import patch, MagicMock
from pyodm.exceptions import OdmError

from app.api.tasks.task import (
    on_task_create,
    on_task_pause,
    on_task_resume,
    on_task_cancel,
    on_task_nodeodm_webhook,
    on_task_finish,
    on_task_failure,
)
from app.api.models.result import ODMTaskResult
from app.api.constants.odm import ODMTaskStatus, ODMProcessingStage, ODMTaskResultType


@pytest.fixture
def mock_nodeodm():
    """Mock NodeODMClient and all its return values."""
    with patch("app.api.tasks.task.NodeODMClient") as mock_client_cls:
        mock_node = MagicMock()
        mock_task = MagicMock()

        mock_client_cls.for_task.return_value = mock_node
        mock_node.get_task.return_value = mock_task
        mock_node.create_task.return_value = mock_task

        mock_task.cancel.return_value = True
        mock_task.restart.return_value = True
        mock_task.remove.return_value = True

        yield {
            "client_cls": mock_client_cls,
            "node": mock_node,
            "task": mock_task,
        }


@pytest.fixture
def temp_image_file_factory():
    """Factory that creates a fresh temporary image file each time."""
    import io
    from PIL import Image as PILImage
    from django.core.files.uploadedfile import SimpleUploadedFile

    def _create(name="test.jpg"):
        image = PILImage.new("RGB", (300, 300), color="red")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)

        return SimpleUploadedFile(
            name=name,
            content=buffer.getvalue(),
            content_type="image/jpeg",
        )

    return _create


@pytest.fixture
def workspace_with_images(workspace_factory, image_factory, temp_image_file_factory):
    """Create a workspace populated with test images."""
    workspace = workspace_factory()
    for i in range(3):
        image_file = temp_image_file_factory(name=f"test_{i}.jpg")
        image_factory(workspace=workspace, image_file=image_file)
    image_factory(workspace=workspace, image_file=image_file, is_thumbnail=True)
    return workspace


@pytest.fixture
def odm_task(odm_task_factory, workspace_with_images):
    """Create an ODMTask linked to a workspace with images."""
    return odm_task_factory(workspace=workspace_with_images)


@pytest.fixture
def create_task_result_files(settings, tmp_path):
    def _create(odm_task, result_types=None):
        if result_types is None:
            result_types = [
                ODMTaskResultType.ORTHOPHOTO_GEOTIFF,
                ODMTaskResultType.POINT_CLOUD_LAZ,
                ODMTaskResultType.DSM,
                ODMTaskResultType.REPORT,
            ]

        odm_task.task_dir.mkdir(parents=True, exist_ok=True)

        for result_type in result_types:
            file_path = odm_task.task_dir / result_type.relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(f"dummy content for {result_type.name}".encode())

        return result_types

    return _create


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestOnTaskCreate:
    def test_success(self, mock_nodeodm, odm_task):
        on_task_create.apply(args=[odm_task.uuid]).get()

        mock_nodeodm["client_cls"].for_task.assert_called_once_with(odm_task.uuid)
        mock_nodeodm["node"].create_task.assert_called_once()

        call_kwargs = mock_nodeodm["node"].create_task.call_args.kwargs
        assert "files" in call_kwargs
        assert "options" in call_kwargs
        assert len(call_kwargs["files"]) == 3

        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.RUNNING

    def test_task_not_found(self, mock_nodeodm):
        on_task_create.apply(args=[uuid4()]).get()
        mock_nodeodm["node"].create_task.assert_not_called()

    def test_odm_error_fails_task(self, mock_nodeodm, odm_task):
        mock_nodeodm["node"].create_task.side_effect = OdmError("Connection refused")
        on_task_create.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_unexpected_error_fails_task(self, mock_nodeodm, odm_task):
        mock_nodeodm["node"].create_task.side_effect = RuntimeError("Unexpected")
        on_task_create.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestOnTaskPause:
    def test_success(self, mock_nodeodm, odm_task):
        odm_task.status = ODMTaskStatus.RUNNING
        odm_task.save()
        on_task_pause.apply(args=[odm_task.uuid]).get()
        mock_nodeodm["node"].get_task.assert_called_once_with(str(odm_task.uuid))
        mock_nodeodm["task"].cancel.assert_called_once()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.PAUSED

    def test_cancel_returns_false_fails_task(self, mock_nodeodm, odm_task):
        mock_nodeodm["task"].cancel.return_value = False
        on_task_pause.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_odm_error_fails_task(self, mock_nodeodm, odm_task):
        mock_nodeodm["node"].get_task.side_effect = OdmError("Node unavailable")
        on_task_pause.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestOnTaskResume:
    def test_success(self, mock_nodeodm, odm_task):
        odm_task.status = ODMTaskStatus.PAUSED
        odm_task.save()

        on_task_resume.apply(args=[odm_task.uuid]).get()

        mock_nodeodm["task"].restart.assert_called_once()
        assert "options" in mock_nodeodm["task"].restart.call_args.kwargs

        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.RUNNING

    def test_restart_returns_false_fails_task(self, mock_nodeodm, odm_task):
        mock_nodeodm["task"].restart.return_value = False

        on_task_resume.apply(args=[odm_task.uuid]).get()

        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestOnTaskCancel:
    def test_success(self, mock_nodeodm, odm_task):
        on_task_cancel.apply(args=[odm_task.uuid]).get()
        mock_nodeodm["task"].remove.assert_called_once()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.CANCELLED

    def test_remove_returns_false_fails_task(self, mock_nodeodm, odm_task):
        mock_nodeodm["task"].remove.return_value = False
        on_task_cancel.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestOnTaskNodeodmWebhook:
    def test_success_creates_previous_stage_results(
        self, mock_nodeodm, odm_task, create_task_result_files
    ):
        # Set task to a stage that has a previous stage with results
        stage = ODMProcessingStage.ODM_DEM
        odm_task.step = stage
        odm_task.save()

        expected_types = create_task_result_files(
            odm_task, stage.previous_stage.stage_results
        )
        on_task_nodeodm_webhook.apply(args=[odm_task.uuid]).get()
        mock_nodeodm["task"].restart.assert_called_once()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.RUNNING

        if expected_types:
            results = ODMTaskResult.objects.filter(workspace=odm_task.workspace)
            assert results.count() == len(expected_types)
            assert {r.result_type for r in results} == {t for t in expected_types}

    def test_success_no_previous_stage(self, mock_nodeodm, odm_task):
        # First stage has no previous stage
        stage = ODMProcessingStage.DATASET
        odm_task.step = stage
        odm_task.save()
        on_task_nodeodm_webhook.apply(args=[odm_task.uuid]).get()
        mock_nodeodm["task"].restart.assert_called_once()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.RUNNING
        assert ODMTaskResult.objects.filter(workspace=odm_task.workspace).count() == 0

    def test_success_no_result_files_exist(self, mock_nodeodm, odm_task):
        stage = ODMProcessingStage.ODM_DEM
        odm_task.step = stage
        odm_task.save()
        on_task_nodeodm_webhook.apply(args=[odm_task.uuid]).get()
        mock_nodeodm["task"].restart.assert_called_once()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.RUNNING

    def test_restart_fails(self, mock_nodeodm, odm_task):
        mock_nodeodm["task"].restart.return_value = False
        on_task_nodeodm_webhook.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_odm_error_fails_task(self, mock_nodeodm, odm_task):
        mock_nodeodm["node"].get_task.side_effect = OdmError("Node down")
        on_task_nodeodm_webhook.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestOnTaskFinish:
    def test_success(self, mock_nodeodm, odm_task):
        on_task_finish.apply(args=[odm_task.uuid]).get()

        mock_nodeodm["task"].remove.assert_called_once()

        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.COMPLETED

    def test_cleanup_fails(self, mock_nodeodm, odm_task):
        mock_nodeodm["task"].remove.return_value = False
        on_task_finish.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_odm_error_fails_task(self, mock_nodeodm, odm_task):
        mock_nodeodm["node"].get_task.side_effect = OdmError("Node down")
        on_task_finish.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_task_not_found(self, mock_nodeodm):
        on_task_finish.apply(args=[uuid4()]).get()
        mock_nodeodm["task"].remove.assert_not_called()


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestOnTaskFailure:
    def test_success(self, mock_nodeodm, odm_task):
        on_task_failure.apply(args=[odm_task.uuid]).get()
        mock_nodeodm["node"].get_task.assert_called_once_with(str(odm_task.uuid))
        mock_nodeodm["task"].remove.assert_called_once()
        odm_task.refresh_from_db()
        assert odm_task.status == ODMTaskStatus.FAILED

    def test_cleanup_fails(self, mock_nodeodm, odm_task):
        mock_nodeodm["task"].remove.return_value = False
        on_task_failure.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_odm_error_fails_task(self, mock_nodeodm, odm_task):
        mock_nodeodm["node"].get_task.side_effect = OdmError("Node down")
        on_task_failure.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_task_not_found(self, mock_nodeodm):
        on_task_failure.apply(args=[uuid4()]).get()
        mock_nodeodm["task"].remove.assert_not_called()
