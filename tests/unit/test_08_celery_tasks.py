import pytest
from uuid import uuid4
from unittest.mock import patch

from app.api.tasks.task import (
    on_task_create,
    on_task_pause,
    on_task_resume,
    on_task_cancel,
    on_task_nodeodm_webhook,
    on_task_finish,
    on_task_failure,
)
from app.api.tasks.workspace import on_workspace_images_uploaded
from app.api.models.image import Image
from app.api.models.result import ODMTaskResult
from app.api.constants.odm import ODMTaskStatus, ODMProcessingStage, ODMTaskResultType


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
    workspace = workspace_factory()
    for i in range(3):
        image_file = temp_image_file_factory(name=f"test_{i}.jpg")
        image_factory(workspace=workspace, image_file=image_file)
    image_factory(workspace=workspace, image_file=image_file, is_thumbnail=True)
    return workspace


@pytest.fixture
def odm_task(odm_task_factory, workspace_with_images):
    return odm_task_factory(workspace=workspace_with_images)


@pytest.fixture
def initialized_mock_task(mock_odm_server, odm_task):
    return mock_odm_server.manager.create_init(str(odm_task.uuid), odm_task.name, [])


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
    def test_success(self, mock_odm_server, odm_task):
        on_task_create.apply(args=[odm_task.uuid]).get()
        remote_task = mock_odm_server.manager.get_task(str(odm_task.uuid))
        assert remote_task is not None
        assert remote_task.name == odm_task.name
        if odm_task.options:
            assert remote_task.options == odm_task.options
        assert remote_task.imagesCount >= 3
        assert remote_task.status.code == 20 # RUNNING
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.RUNNING

    def test_task_not_found_locally(self, mock_odm_server):
        random_uuid = uuid4()
        try:
            on_task_create.apply(args=[random_uuid]).get()
        except Exception:
            pass # We don't care about the local exception, we care about the side effect

        assert len(mock_odm_server.manager.list_uuids()) == 0

    def test_odm_init_error_fails_task(self, httpserver, odm_task):
        httpserver.expect_request("/task/new/init").respond_with_json(
            {"error": "Server on fire"}, status=500
        )
        on_task_create.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_odm_upload_error_fails_task(self, httpserver, odm_task):
        import re
        upload_pattern = re.compile(r"^/task/new/upload/.*$")
        httpserver.expect_request(uri=upload_pattern, method="POST").respond_with_json(
            {"error": "Disk full"}, status=500
        )

        on_task_create.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestOnTaskPause:
    def test_success(self, initialized_mock_task, odm_task):
        odm_task.status = ODMTaskStatus.RUNNING
        odm_task.save()
        initialized_mock_task.commit() 
        assert initialized_mock_task.status.code == 20 # RUNNING
        on_task_pause.apply(args=[odm_task.uuid]).get()
        assert initialized_mock_task.status.code == 50 # CANCELED/PAUSED
        assert any("canceled" in log.lower() for log in initialized_mock_task.output)
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.PAUSED

    def test_cancel_returns_false_fails_task(self, mock_odm_server, odm_task):
        on_task_pause.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_node_500_error_fails_task(self, httpserver, odm_task):
        httpserver.expect_request("/task/cancel", method="POST").respond_with_json(
            {"error": "Internal Server Error"}, status=500
        )
        on_task_pause.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_pause_idempotency(self, initialized_mock_task, odm_task):
        initialized_mock_task.cancel()
        on_task_pause.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.PAUSED


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestOnTaskResume:
    def test_success(self, initialized_mock_task, odm_task):
        initialized_mock_task.cancel() 
        assert initialized_mock_task.status.code == 50 # CANCELED/PAUSED
        odm_task.status = ODMTaskStatus.PAUSED
        odm_task.save()
        on_task_resume.apply(args=[odm_task.uuid]).get()
        assert initialized_mock_task.status.code == 10
        assert initialized_mock_task.progress == 0.0
        assert any("restarted" in log.lower() for log in initialized_mock_task.output)
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.RUNNING

    def test_restart_fails_on_server(self, mock_odm_server, odm_task):
        on_task_resume.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_node_500_error_fails_task(self, httpserver, odm_task):
        httpserver.expect_request("/task/restart", method="POST").respond_with_json(
            {"error": "Internal Server Error"}, status=500
        )
        on_task_resume.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_resume_passes_correct_options(self, initialized_mock_task, odm_task):
        odm_task.options = {
            odm_task.step: {
                "dsm": True,
            }
        }       
        odm_task.status = ODMTaskStatus.PAUSED
        odm_task.save()
        on_task_resume.apply(args=[odm_task.uuid]).get()
        assert {"name": "dsm", "value": True} in initialized_mock_task.options


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestOnTaskCancel:
    def test_success(self, initialized_mock_task, odm_task):
        on_task_cancel.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.CANCELLED

    def test_remove_returns_false_fails_task(self, mock_odm_server, odm_task):
        on_task_cancel.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_node_error_fails_task(self, httpserver, odm_task):
        httpserver.expect_request("/task/remove", method="POST").respond_with_json(
            {"error": "Internal Server Error"}, status=500
        )
        on_task_cancel.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestOnTaskNodeodmWebhook:
    def test_success_with_restarting(
        self, initialized_mock_task, odm_task, create_task_result_files
    ):
        stage = ODMProcessingStage.ODM_DEM
        odm_task.step = stage
        odm_task.save()
        expected_types = create_task_result_files(
            odm_task, stage.previous_stage.stage_results
        )
        on_task_nodeodm_webhook.apply(args=[odm_task.uuid]).get()
        assert initialized_mock_task.status.code == 10 
        assert initialized_mock_task.progress == 0.0
        assert any("restarted" in log.lower() for log in initialized_mock_task.output)
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.RUNNING
        if expected_types:
            results = ODMTaskResult.objects.filter(workspace=odm_task.workspace)
            assert results.count() == len(expected_types)
            assert {r.result_type for r in results} == set(expected_types)

    def test_restart_fails_on_server(self, mock_odm_server, odm_task):
        on_task_nodeodm_webhook.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_node_crash_during_webhook(self, httpserver, odm_task):
        httpserver.expect_request("/task/restart", method="POST").respond_with_json(
            {"error": "NodeODM out of memory"}, status=500
        )
        on_task_nodeodm_webhook.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_success_no_previous_stage_results(self, initialized_mock_task, odm_task):
        odm_task.step = ODMProcessingStage.DATASET
        odm_task.save()
        on_task_nodeodm_webhook.apply(args=[odm_task.uuid]).get()
        assert initialized_mock_task.status.code == 10
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.RUNNING
        assert ODMTaskResult.objects.filter(workspace=odm_task.workspace).count() == 0


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestOnTaskFinish:
    def test_success(self, initialized_mock_task, odm_task):
        on_task_finish.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.COMPLETED

    def test_cleanup_returns_false_fails_task(self, mock_odm_server, odm_task):
        on_task_finish.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_node_error_fails_task(self, httpserver, odm_task):
        httpserver.expect_request("/task/remove", method="POST").respond_with_json(
            {"error": "Service Unavailable"}, status=503
        )
        on_task_finish.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_task_not_found_locally(self, mock_odm_server):
        random_uuid = uuid4()
        on_task_finish.apply(args=[random_uuid]).get()
        assert len(mock_odm_server.manager.list_uuids()) == 0


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestOnTaskFailure:
    def test_success(self, initialized_mock_task, odm_task):
        on_task_failure.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_cleanup_fails_locally_still_fails_task(self, mock_odm_server, odm_task):
        on_task_failure.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_odm_error_fails_task(self, httpserver, odm_task):
        httpserver.expect_request("/task/remove", method="POST").respond_with_json(
            {"error": "Explosion"}, status=500
        )
        on_task_failure.apply(args=[odm_task.uuid]).get()
        odm_task.refresh_from_db()
        assert odm_task.odm_status == ODMTaskStatus.FAILED

    def test_task_not_found_in_local_db(self, mock_odm_server):
        random_uuid = uuid4()
        on_task_failure.apply(args=[random_uuid]).get()
        assert len(mock_odm_server.manager.list_uuids()) == 0


@pytest.mark.django_db
class TestOnWorkspaceImagesUploaded:
    def test_makes_thumbnail_for_each_image(self, image_factory):
        image1 = image_factory()
        image2 = image_factory()

        with patch.object(Image, "make_thumbnail") as mock_make_thumbnail:
            on_workspace_images_uploaded.apply(args=([image1.uuid, image2.uuid],))

        assert mock_make_thumbnail.call_count == 2

    def test_ignores_images_not_in_uuid_list(self, image_factory):
        included = image_factory()
        excluded = image_factory()

        with patch.object(Image, "make_thumbnail") as mock_make_thumbnail:
            on_workspace_images_uploaded.apply(args=([included.uuid],))

        mock_make_thumbnail.assert_called_once()

    def test_handles_empty_uuid_list(self):
        with patch.object(Image, "make_thumbnail") as mock_make_thumbnail:
            on_workspace_images_uploaded.apply(args=([],))

        mock_make_thumbnail.assert_not_called()

    def test_nonexistent_uuids_are_safely_ignored(self, image_factory):
        image = image_factory()
        missing_uuid = uuid4()

        with patch.object(Image, "make_thumbnail") as mock_make_thumbnail:
            on_workspace_images_uploaded.apply(args=([image.uuid, missing_uuid],))

        mock_make_thumbnail.assert_called_once()
