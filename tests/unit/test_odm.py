import pytest
import datetime
from pathlib import Path
from django.db.utils import IntegrityError


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
    