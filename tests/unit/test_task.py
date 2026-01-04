import pytest
import datetime

from app.api.constants.odm import ODMTaskStatus, ODMProcessingStage


@pytest.mark.django_db
class TestODMTask:
    def test_task_creation(self, odm_task_factory):
        task = odm_task_factory(status=ODMTaskStatus.RUNNING.value, step=ODMProcessingStage.MVS.value)
        assert task.odm_status == ODMTaskStatus.RUNNING
        assert task.odm_step == ODMProcessingStage.MVS
        assert task.uuid is not None
        assert isinstance(task.created_at, datetime.datetime)
        assert task.workspace.uuid is not None
        
    def test_task_dir_property(self, odm_task_factory, tmp_path, settings):
        setattr(settings, "TASKS_DIR", tmp_path)
        task = odm_task_factory()
        expected_path = tmp_path / str(task.workspace.uuid) / str(task.uuid)
        assert task.task_dir == expected_path

    def test_get_current_step_options_returns_dict(self, odm_task_factory):
        task = odm_task_factory(options={ODMProcessingStage.DATASET.value: {"param": 123}})
        options = task.get_current_step_options()
        assert isinstance(options, dict)
        if task.odm_step == ODMProcessingStage.DATASET:
            assert options.get("param") == 123
