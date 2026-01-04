import pytest
import datetime


@pytest.mark.django_db
class TestWorkspace:
    def test_workspace_creation(self, workspace_factory):
        workspace = workspace_factory(name="Project Alpha")
        assert workspace.name == "Project Alpha"
        assert isinstance(workspace.uuid, str) or workspace.uuid is not None
        assert isinstance(workspace.created_at, datetime.datetime) or workspace.uuid is not None
        assert workspace.user_id is not None
        assert isinstance(workspace.user_id, int)
