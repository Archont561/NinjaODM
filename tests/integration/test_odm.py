import pytest

from app.api.models.workspace import Workspace


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
        assert response.status_code == 200

    def test_get_workspace(self, service_api_client, workspace_factory):
        ws = workspace_factory(user_id=1234, name="Other WS")
        resp = service_api_client.get(f"internal/workspaces/{ws.uuid}")
        assert resp.status_code == 200

    def test_update_workspace(self, service_api_client, workspace_factory):
        ws = workspace_factory(user_id=1234, name="Other WS")
        resp = service_api_client.patch(
            f"internal/workspaces/{ws.uuid}", 
            json={"name": "Updated"}
        )
        assert resp.status_code == 200
        
        ws.refresh_from_db()
        assert ws.name == "Updated"

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
        assert resp.status_code == 200
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
