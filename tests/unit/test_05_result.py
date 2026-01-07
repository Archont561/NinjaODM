import pytest
import datetime
from pathlib import Path
from django.core.files import File

from app.api.constants.odm import ODMTaskResultType


@pytest.mark.django_db
class TestODMTaskResult:
    def test_task_result_creation(self, odm_task_result_factory):
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
                file=File(f, name=temp_file.name),
            )

        assert task_result.file.name is not None
        uploaded_file_path = Path(task_result.file.path)
        assert uploaded_file_path.exists()
        assert uploaded_file_path.read_text() == "This is a test file"
        expected_path = (
            Path(settings.MEDIA_ROOT)
            / settings.RESULTS_DIR_NAME
            / str(task_result.workspace.uuid)
        )
        assert uploaded_file_path.parent == expected_path
