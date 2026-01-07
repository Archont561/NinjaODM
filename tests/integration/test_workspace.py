import pytest
from datetime import timedelta
from django.utils import timezone
from ninja_extra.testing import TestClient

from app.api.models.workspace import Workspace
from app.api.controllers.workspace import (
    WorkspaceControllerInternal,
    WorkspaceControllerPublic,
)
from ..auth_clients import AuthStrategyEnum, AuthenticatedTestClient


@pytest.fixture
def workspace_list(workspace_factory):
    now = timezone.now()

    def create_workspace(name, user_id, days_ago):
        return workspace_factory(
            name=name,
            user_id=user_id,
            created_at=now - timedelta(days=days_ago)
        )

    return [
        create_workspace("ProjectA",      999, 10),
        create_workspace("ProjectB",      999,  5),
        create_workspace("SharedProject", 999,  3),
        create_workspace("ProjectC",      999,  1),
        create_workspace("OtherUser1",      1,  8),
        create_workspace("OtherProject",    3,  6),
        create_workspace("OtherUser2",      2,  2),
    ]


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestWorkspaceAPIInternal:
    @classmethod
    def setup_method(cls):
        cls.client = AuthenticatedTestClient(
            WorkspaceControllerInternal, auth=AuthStrategyEnum.service
        )

    @pytest.mark.parametrize(
        "query_format, expected_count",
        [
            ("", 7),
            ("name=ProjectA", 1),
            ("name=Project", 5),
            ("name=NonExistent", 0),
            ("created_after={after}", 4),
            ("created_before={before}", 6),
            ("name=Project&created_after={after}", 3),
            ("name=ProjectC&created_after={after}", 1),
        ],
    )
    def test_list_workspaces_filtering(
        self, workspace_list, query_format, expected_count
    ):
        now = timezone.now()
        after_date = (now - timedelta(days=6)).isoformat().replace("+00:00", "Z")
        before_date = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
        query = query_format.format(after=after_date, before=before_date)
        url = "/" + f"?{query}" if query else ""
        resp = self.client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == expected_count, f"Failed for query: {query}"

    def test_create_workspace(self):
        payload = {"name": "Service WS", "user_id": 1234}
        response = self.client.post("/", json=payload)
        assert response.status_code == 201

    def test_get_workspace(self, workspace_factory):
        ws = workspace_factory(user_id=1234, name="Other WS")
        resp = self.client.get(f"/{ws.uuid}")
        assert resp.status_code == 200

    def test_update_workspace(self, workspace_factory):
        ws = workspace_factory(user_id=1234, name="Other WS")
        resp = self.client.patch(
            f"/{ws.uuid}", json={"name": "Updated", "user_id": 333}
        )
        assert resp.status_code == 200

        ws.refresh_from_db()
        assert ws.name == "Updated"
        assert ws.user_id == 333

    def test_delete_workspace(self, workspace_factory):
        ws = workspace_factory(user_id=1234, name="Other WS")
        resp = self.client.delete(f"/{ws.uuid}")
        assert resp.status_code == 204

        with pytest.raises(Workspace.DoesNotExist):
            Workspace.objects.get(uuid=ws.uuid)


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestWorkspaceAPIPublic:
    @classmethod
    def setup_method(cls):
        cls.client = AuthenticatedTestClient(
            WorkspaceControllerPublic, auth=AuthStrategyEnum.jwt
        )

    @pytest.mark.parametrize(
        "query_format, expected_count",
        [
            ("", 4),
            ("name=ProjectA", 1),
            ("name=Project", 4),
            ("name=NonExistent", 0),
            ("created_after={after}", 3),
            ("created_before={before}", 3),
            ("name=Project&created_after={after}", 3),
            ("name=ProjectC&created_after={after}", 1),
        ],
    )
    def test_list_workspaces_filtering(
        self, workspace_list, query_format, expected_count
    ):
        now = timezone.now()
        after_date = (now - timedelta(days=6)).isoformat().replace("+00:00", "Z")
        before_date = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
        query = query_format.format(after=after_date, before=before_date)
        url = "/" + f"?{query}" if query else ""
        resp = self.client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == expected_count, f"Failed for query: {query}"

    @pytest.fixture
    def user_workspace(self, workspace_factory):
        return workspace_factory(user_id=999, name="User WS")

    @pytest.fixture
    def other_workspace(self, workspace_factory):
        return workspace_factory(user_id=1234, name="Other WS")

    def test_create_workspace(self):
        payload = {"name": "JWT WS"}
        resp = self.client.post("/", json=payload)
        assert resp.status_code == 201
        ws = Workspace.objects.get(uuid=resp.json()["uuid"])
        assert ws.name == "JWT WS"
        assert ws.user_id == 999

    def test_get_own_workspace(self, user_workspace):
        resp = self.client.get(f"/{user_workspace.uuid}")
        assert resp.status_code == 200
        assert resp.json()["uuid"] == str(user_workspace.uuid)

    def test_get_other_workspace_denied(self, other_workspace):
        resp = self.client.get(f"/{other_workspace.uuid}")
        assert resp.status_code in (403, 404)

    def test_update_own_workspace(self, user_workspace):
        resp = self.client.patch(f"/{user_workspace.uuid}", json={"name": "Updated"})
        assert resp.status_code == 200
        user_workspace.refresh_from_db()
        assert user_workspace.name == "Updated"

    def test_update_other_workspace_denied(self, other_workspace):
        resp = self.client.patch(f"/{other_workspace.uuid}", json={"name": "Hack"})
        assert resp.status_code in (403, 404)

    def test_delete_own_workspace(self, user_workspace):
        resp = self.client.delete(f"/{user_workspace.uuid}")
        assert resp.status_code == 204
        with pytest.raises(Workspace.DoesNotExist):
            Workspace.objects.get(uuid=user_workspace.uuid)

    def test_delete_other_workspace_denied(self, other_workspace):
        resp = self.client.delete(f"/{other_workspace.uuid}")
        assert resp.status_code in (403, 404)

    def test_upload_image_own_workspace(self, user_workspace, temp_image_file):
        resp = self.client.post(
            f"/{user_workspace.uuid}/upload-image",
            **{"FILES": {"image_file": temp_image_file}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["uuid"] is not None
        assert data["workspace_uuid"] == str(user_workspace.uuid)

    def test_upload_image_other_workspace_denied(
        self, other_workspace, temp_image_file
    ):
        resp = self.client.post(
            f"/{other_workspace.uuid}/upload-image",
            **{"FILES": {"image_file": temp_image_file}},
        )
        assert resp.status_code in (403, 404)


@pytest.mark.django_db
class TestWorkspaceAPIUnauthorized:
    @classmethod
    def setup_method(cls):
        cls.public_client = TestClient(WorkspaceControllerPublic)
        cls.internal_client = TestClient(WorkspaceControllerInternal)
        cls.user_client = AuthenticatedTestClient(
            WorkspaceControllerInternal, auth=AuthStrategyEnum.jwt
        )

    @pytest.mark.parametrize(
        "client_type, method, url_template, payload",
        [
            # Public client
            ("public_client", "get", "/", None),
            ("public_client", "post", "/", {"name": "Fail"}),
            ("public_client", "get", "/{uuid}", None),
            ("public_client", "patch", "/{uuid}", {"name": "Fail"}),
            ("public_client", "delete", "/{uuid}", None),
            # Internal client
            ("internal_client", "get", "/", None),
            ("internal_client", "post", "/", {"name": "Fail", "user_id": 999}),
            ("internal_client", "get", "/{uuid}", None),
            ("internal_client", "patch", "/{uuid}", {"name": "Fail"}),
            ("internal_client", "delete", "/{uuid}", None),
            # User client
            ("user_client", "get", "/", None),
            ("user_client", "post", "/", {"name": "Fail"}),
            ("user_client", "get", "/{uuid}", None),
            ("user_client", "patch", "/{uuid}", {"name": "Fail"}),
            ("user_client", "delete", "/{uuid}", None),
        ],
    )
    def test_access_denied(
        self, workspace_factory, client_type, method, url_template, payload
    ):
        ws = workspace_factory(user_id=999)
        client = getattr(self, client_type)
        url = url_template.format(uuid=ws.uuid)
        response = getattr(client, method)(url, json=payload)
        assert response.status_code in (401, 403)
        if method == "delete":
            assert Workspace.objects.filter(pk=ws.pk).exists()
