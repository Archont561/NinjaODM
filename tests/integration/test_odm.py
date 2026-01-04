import pytest

from app.api.models.workspace import Workspace
from app.api.models.task import ODMTask
from app.api.constants.odm import ODMTaskStatus


@pytest.mark.django_db
class TestWorkspaceAPIService:
    """Tests for HMAC service client (full access to all workspaces)"""

    def test_list_workspaces(self, service_api_client, workspace_factory):
        workspace_factory.create_batch(3, user_id=999)
        workspace_factory(user_id=1234)
        response = service_api_client.get("internal/workspaces/")
        assert response.status_code == 200
        data = response.json()
        # Should see all workspaces
        assert len(data) >= 4

    def test_create_workspace(self, service_api_client):
        payload = {"name": "Service WS", "user_id": 1234}
        response = service_api_client.post("internal/workspaces/", json=payload)
        assert response.status_code == 201

    def test_get_workspace(self, service_api_client, workspace_factory):
        ws = workspace_factory(user_id=1234, name="Other WS")
        resp = service_api_client.get(f"internal/workspaces/{ws.uuid}")
        assert resp.status_code == 200

    def test_update_workspace(self, service_api_client, workspace_factory):
        ws = workspace_factory(user_id=1234, name="Other WS")
        resp = service_api_client.patch(
            f"internal/workspaces/{ws.uuid}", 
            json={"name": "Updated", "user_id": 333}
        )
        assert resp.status_code == 200
        
        ws.refresh_from_db()
        assert ws.name == "Updated"
        assert ws.user_id == 333

    def test_delete_workspace(self, service_api_client, workspace_factory):
        ws = workspace_factory(user_id=1234, name="Other WS")
        resp = service_api_client.delete(f"internal/workspaces/{ws.uuid}")
        assert resp.status_code == 204
        
        with pytest.raises(Workspace.DoesNotExist):
            Workspace.objects.get(uuid=ws.uuid)


@pytest.mark.django_db
class TestWorkspaceAPIServiceUser:
    """Tests for JWT service-user client (access only own workspaces)"""

    @pytest.fixture
    def user_workspace(self, workspace_factory):
        # valid_token fixture in conftest uses user_id = 999
        return workspace_factory(user_id=999, name="My WS")

    @pytest.fixture
    def other_workspace(self, workspace_factory):
        return workspace_factory(user_id=1234, name="Other WS")

    def test_list_workspaces_sees_only_own(self, service_user_api_client, user_workspace, other_workspace):
        response = service_user_api_client.get("/workspaces/")
        assert response.status_code == 200
        data = response.json()
        # Should only see workspace owned by user_id=999
        assert len(data) == 1
        assert data[0]["uuid"] == str(user_workspace.uuid)

    def test_create_workspace(self, service_user_api_client):
        payload = {"name": "JWT WS"}
        resp = service_user_api_client.post("/workspaces/", json=payload)
        assert resp.status_code == 201
        ws = Workspace.objects.get(uuid=resp.json()["uuid"])
        assert ws.name == "JWT WS"
        assert ws.user_id == 999

    def test_get_own_workspace(self, service_user_api_client, user_workspace):
        resp = service_user_api_client.get(f"/workspaces/{user_workspace.uuid}")
        assert resp.status_code == 200
        assert resp.json()["uuid"] == str(user_workspace.uuid)

    def test_get_other_workspace_denied(self, service_user_api_client, other_workspace):
        resp = service_user_api_client.get(f"/workspaces/{other_workspace.uuid}")
        assert resp.status_code in (403, 404)

    def test_update_own_workspace(self, service_user_api_client, user_workspace):
        resp = service_user_api_client.patch(f"/workspaces/{user_workspace.uuid}", json={"name": "Updated"})
        assert resp.status_code == 200
        user_workspace.refresh_from_db()
        assert user_workspace.name == "Updated"

    def test_update_other_workspace_denied(self, service_user_api_client, other_workspace):
        resp = service_user_api_client.patch(f"/workspaces/{other_workspace.uuid}", json={"name": "Hack"})
        assert resp.status_code in (403, 404)

    def test_delete_own_workspace(self, service_user_api_client, user_workspace):
        resp = service_user_api_client.delete(f"/workspaces/{user_workspace.uuid}")
        assert resp.status_code == 204
        with pytest.raises(Workspace.DoesNotExist):
            Workspace.objects.get(uuid=user_workspace.uuid)

    def test_delete_other_workspace_denied(self, service_user_api_client, other_workspace):
        resp = service_user_api_client.delete(f"/workspaces/{other_workspace.uuid}")
        assert resp.status_code in (403, 404)


@pytest.mark.django_db
class TestWorkspaceAPIUnauthorizedClient:
    """Tests that non-authorized clients cannot access public or internal workspaces."""

    def test_public_workspace_access_denied(self, api_client, workspace_factory):
        """Public API (/workspaces) should deny access without JWT token."""
        ws = workspace_factory(user_id=999)

        # List
        resp = api_client.get("/workspaces/")
        assert resp.status_code in (401, 403)

        # Create
        resp = api_client.post("/workspaces/", json={"name": "Fail"})
        assert resp.status_code in (401, 403)

        # Get
        resp = api_client.get(f"/workspaces/{ws.uuid}")
        assert resp.status_code in (401, 403)

        # Update
        resp = api_client.patch(f"/workspaces/{ws.uuid}", json={"name": "Fail"})
        assert resp.status_code in (401, 403)

        # Delete
        resp = api_client.delete(f"/workspaces/{ws.uuid}")
        assert resp.status_code in (401, 403)

    def test_internal_workspace_access_denied(self, api_client, workspace_factory):
        """Internal API (/internal/workspaces) should deny access without HMAC auth."""
        ws = workspace_factory(user_id=999)

        # List
        resp = api_client.get("/internal/workspaces/")
        assert resp.status_code in (401, 403)

        # Create
        payload = {"user_id": 999, "name": "Fail"}
        resp = api_client.post("/internal/workspaces/", json=payload)
        assert resp.status_code in (401, 403)

        # Get
        resp = api_client.get(f"/internal/workspaces/{ws.uuid}")
        assert resp.status_code in (401, 403)

        # Update
        resp = api_client.patch(f"/internal/workspaces/{ws.uuid}", json={"name": "Fail"})
        assert resp.status_code in (401, 403)

        # Delete
        resp = api_client.delete(f"/internal/workspaces/{ws.uuid}")
        assert resp.status_code in (401, 403)


@pytest.mark.django_db
class TestTaskAPIService:
    """Tests for HMAC service client (full access to all tasks)"""

    def test_list_tasks(self, service_api_client, workspace_factory, odm_task_factory):
        ws1 = workspace_factory(user_id=1)
        ws2 = workspace_factory(user_id=2)

        odm_task_factory.create_batch(2, workspace=ws1)
        odm_task_factory.create_batch(3, workspace=ws2)

        resp = service_api_client.get("internal/tasks/")
        assert resp.status_code == 200
        data = resp.json()
        # Should see all tasks from all workspaces
        assert len(data) >= 5

    def test_create_task(self, service_api_client, workspace_factory, monkeypatch, settings, tmp_path):
        settings.TASKS_DIR = tmp_path
        ws = workspace_factory(user_id=1234)
        payload = {
            "options": {},
        }
        resp = service_api_client.post(f"internal/tasks/?workspace_uuid={ws.uuid}", json=payload)
        assert resp.status_code == 201

        body = resp.json()
        task = ODMTask.objects.get(uuid=body["uuid"])
        assert task.workspace.uuid == ws.uuid
        assert task.task_dir.exists()

    def test_get_task(self, service_api_client, odm_task_factory):
        task = odm_task_factory()
        resp = service_api_client.get(f"internal/tasks/{task.uuid}")
        assert resp.status_code == 200
        assert resp.json()["uuid"] == str(task.uuid)

    @pytest.mark.parametrize("status", ODMTaskStatus.terminal_states())
    def test_delete_terminal_task(
        self, service_api_client, odm_task_factory, status
    ):
        task = odm_task_factory(status=status)
        resp = service_api_client.delete(f"internal/tasks/{task.uuid}")

        assert resp.status_code == 204
        assert not ODMTask.objects.filter(uuid=task.uuid).exists()
    
    @pytest.mark.parametrize("status", ODMTaskStatus.non_terminal_states())
    def test_cannot_delete_non_terminal_task(
        self, service_api_client, odm_task_factory, status
    ):
        task = odm_task_factory(status=status)
        resp = service_api_client.delete(f"internal/tasks/{task.uuid}")

        assert resp.status_code in (400, 403)
        assert ODMTask.objects.filter(uuid=task.uuid).exists()

    @pytest.mark.parametrize(
        "action, expected_status, expected_odm_status",
        [
            ("pause", 200, ODMTaskStatus.PAUSING),
            ("resume", 200, ODMTaskStatus.RESUMING),
            ("cancel", 200, ODMTaskStatus.CANCELLING),
        ]
    )
    def test_custom_actions_change_status(
        self, service_api_client, odm_task_factory, action, expected_status, expected_odm_status
    ):
        task = odm_task_factory()
        resp = service_api_client.post(f"internal/tasks/{task.uuid}/{action}/")
        assert resp.status_code == expected_status
        task.refresh_from_db()
        assert task.odm_status == expected_odm_status


@pytest.mark.django_db
class TestTaskAPIServiceUser:
    """Tests for JWT service-user client (access only own tasks)"""

    @pytest.fixture
    def user_workspace(self, workspace_factory):
        # valid_token fixture uses user_id = 999
        return workspace_factory(user_id=999, name="My WS")

    @pytest.fixture
    def other_workspace(self, workspace_factory):
        return workspace_factory(user_id=1234, name="Other WS")

    @pytest.fixture
    def user_task(self, odm_task_factory, user_workspace):
        return odm_task_factory(workspace=user_workspace)

    @pytest.fixture
    def other_task(self, odm_task_factory, other_workspace):
        return odm_task_factory(workspace=other_workspace)

    def test_list_tasks_sees_only_own(
        self, service_user_api_client, user_task, other_task
    ):
        resp = service_user_api_client.get("/tasks/")
        assert resp.status_code == 200
        data = resp.json()

        # Should only see the task whose workspace belongs to user_id=999
        assert len(data) == 1
        assert data[0]["uuid"] == str(user_task.uuid)
        assert data[0]["workspace_uuid"] == str(user_task.workspace.uuid)

    def test_create_task_in_own_workspace(
        self, service_user_api_client, user_workspace, settings, tmp_path
    ):
        settings.TASKS_DIR = tmp_path
        payload = {
            "options": {},
        }
        resp = service_user_api_client.post(f"/tasks/?workspace_uuid={user_workspace.uuid}", json=payload)
        assert resp.status_code == 201

        body = resp.json()
        task = ODMTask.objects.get(uuid=body["uuid"])
        assert task.workspace.uuid == user_workspace.uuid
        assert task.workspace.user_id == 999
        assert task.status == ODMTaskStatus.QUEUED
        assert task.task_dir.exists()

    def test_create_task_in_other_workspace_denied(
        self, service_user_api_client, other_workspace
    ):
        payload = {
            "options": {},
        }
        resp = service_user_api_client.post(f"/tasks/?workspace_uuid={other_workspace.uuid}", json=payload)
        # Permission (CanCreateTask) should reject this
        assert resp.status_code in (403, 404)

    def test_create_task_without_workspace_uuid_not_allowed(self, service_user_api_client):
        payload = {
            "options": {},
        }
        resp = service_user_api_client.post("/tasks/", json=payload)
        # Permission (CanCreateTask) should reject this
        assert resp.status_code in (403, 404)

    def test_get_own_task(self, service_user_api_client, user_task):
        resp = service_user_api_client.get(f"/tasks/{user_task.uuid}")
        assert resp.status_code == 200
        assert resp.json()["uuid"] == str(user_task.uuid)

    def test_get_other_task_denied(self, service_user_api_client, other_task):
        resp = service_user_api_client.get(f"/tasks/{other_task.uuid}")
        assert resp.status_code in (403, 404)

    @pytest.mark.parametrize("status", ODMTaskStatus.terminal_states())
    def test_delete_own_terminal_task(
        self, service_api_client, user_task, status
    ):
        user_task.status = status
        user_task.save(update_fields=["status"])
        resp = service_api_client.delete(f"internal/tasks/{user_task.uuid}")

        assert resp.status_code == 204
        assert not ODMTask.objects.filter(uuid=user_task.uuid).exists()
    
    @pytest.mark.parametrize("status", ODMTaskStatus.non_terminal_states())
    def test_cannot_delete_own_non_terminal_task(
        self, service_api_client, user_task, status
    ):
        user_task.status = status
        user_task.save(update_fields=["status"])
        resp = service_api_client.delete(f"internal/tasks/{user_task.uuid}")

        assert resp.status_code in (400, 403)
        assert ODMTask.objects.filter(uuid=user_task.uuid).exists()
        
    @pytest.mark.parametrize(
        "action, expected_status, expected_odm_status",
        [
            ("pause", 200, ODMTaskStatus.PAUSING),
            ("resume", 200, ODMTaskStatus.RESUMING),
            ("cancel", 200, ODMTaskStatus.CANCELLING),
        ]
    )
    def test_custom_actions_on_own_task(
        self, service_user_api_client, user_task, action, expected_status, expected_odm_status
    ):
        resp = service_user_api_client.post(f"/tasks/{user_task.uuid}/{action}/")
        assert resp.status_code == expected_status
        user_task.refresh_from_db()
        assert user_task.odm_status == expected_odm_status

    @pytest.mark.parametrize("action", ["pause", "resume", "cancel"])
    def test_action_other_task_denied(self, service_user_api_client, other_task, action):
        original_status = other_task.status
        resp = service_user_api_client.post(f"/tasks/{other_task.uuid}/{action}/")
        assert resp.status_code in (403, 404)
        other_task.refresh_from_db()
        # Status should not have changed
        assert other_task.status == original_status


@pytest.mark.django_db
class TestTaskAPIUnauthorizedClient:
    """Tests that non-authorized clients cannot access public or internal tasks."""

    @pytest.mark.parametrize("endpoint", ["/tasks/", "/internal/tasks/"])
    def test_task_access_denied(
        self, api_client, workspace_factory, odm_task_factory, endpoint
    ):
        ws = workspace_factory(user_id=999)
        task = odm_task_factory(workspace=ws)

        # List
        resp = api_client.get(endpoint)
        assert resp.status_code in (401, 403)

        # Create
        payload = {
            "options": {},
        }
        resp = api_client.post(f"{endpoint}?{ws.uuid}", json=payload)
        assert resp.status_code in (401, 403)

        # Get
        resp = api_client.get(f"{endpoint}{task.uuid}")
        assert resp.status_code in (401, 403)

        # Delete
        resp = api_client.delete(f"{endpoint}{task.uuid}")
        assert resp.status_code in (401, 403)

        # Custom actions
        for action in ("pause", "resume", "cancel"):
            resp = api_client.post(f"{endpoint}{task.uuid}/{action}/")
            assert resp.status_code in (401, 403)
    