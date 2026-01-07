import pytest
from datetime import timedelta
from django.utils import timezone

from app.api.models.workspace import Workspace


@pytest.mark.django_db
class TestWorkspaceAPIInternal:
    @pytest.mark.parametrize(
        "query_params, expected_count",
        [
            # 1. No filters - should see all
            ("", 4),
            # 2. Filter by name (partial match)
            ("name=ProjectA", 1),
            ("name=Project", 2),  # Matches ProjectA and ProjectB
            ("name=NonExistent", 0),
            # 3. Filter by date (After)
            ("created_after={after_date}", 3),
            # 4. Filter by date range (Between)
            ("created_after={after_date}&created_before={before_date}", 1),
            # 5. Combined filters
            ("name=Project&created_after={after_date}", 2),
        ],
    )
    def test_list_workspaces_filtering(
        self, service_api_client, workspace_factory, query_params, expected_count
    ):
        now = timezone.now()
        workspace_factory(name="Old Task", created_at=now - timedelta(days=10))
        workspace_factory(name="ProjectA", created_at=now - timedelta(days=5))
        workspace_factory(name="ProjectB", created_at=now - timedelta(days=1))
        workspace_factory(name="Shared", user_id=999)
        after_date = (now - timedelta(days=6)).isoformat().replace("+00:00", "Z")
        before_date = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
        formatted_query = query_params.format(
            after_date=after_date, before_date=before_date
        )
        url = "/internal/workspaces/"
        if formatted_query:
            url += f"?{formatted_query}"
        response = service_api_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == expected_count, f"Failed for query: {formatted_query}"

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
            f"internal/workspaces/{ws.uuid}", json={"name": "Updated", "user_id": 333}
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
@pytest.mark.usefixtures("mock_redis")
class TestWorkspaceAPIPublic:
    @pytest.fixture
    def user_workspace(self, workspace_factory):
        # valid_token fixture in conftest uses user_id = 999
        return workspace_factory(user_id=999, name="My WS")

    @pytest.fixture
    def other_workspace(self, workspace_factory):
        return workspace_factory(user_id=1234, name="Other WS")

    @pytest.mark.parametrize(
        "workspaces_to_create, query_params, expected_names",
        [
            # 1. No filters – return all user workspaces
            (
                [
                    {"name": "ProjectA", "user_id": 999},
                    {"name": "ProjectB", "user_id": 999},
                    {"name": "OtherUser", "user_id": 1},  # should be ignored
                ],
                "",
                ["ProjectA", "ProjectB"],
            ),
            # 2. Name filter – partial match
            (
                [
                    {"name": "ProjectA", "user_id": 999},
                    {"name": "ProjectB", "user_id": 999},
                    {"name": "ProjectA", "user_id": 1},  # other user
                ],
                "name=ProjectA",
                ["ProjectA"],  # only user's workspace
            ),
            # 3. created_after filter
            (
                [
                    {"name": "Old", "user_id": 999, "days_ago": 10},
                    {"name": "Recent", "user_id": 999, "days_ago": 2},
                ],
                "created_after={after_date}",
                ["Recent"],
            ),
            # 4. created_before filter
            (
                [
                    {"name": "Old", "user_id": 999, "days_ago": 10},
                    {"name": "Recent", "user_id": 999, "days_ago": 2},
                ],
                "created_before={before_date}",
                ["Old"],
            ),
            # 5. Combined filters: name + created_after
            (
                [
                    {"name": "ProjectA", "user_id": 999, "days_ago": 5},
                    {"name": "ProjectB", "user_id": 999, "days_ago": 1},
                    {"name": "ProjectA", "user_id": 1, "days_ago": 1},  # other user
                ],
                "name=ProjectA&created_after={after_date}",
                ["ProjectA"],
            ),
        ],
    )
    def test_list_workspaces_public_filters(
        self,
        service_user_api_client,
        workspace_factory,
        workspaces_to_create,
        query_params,
        expected_names,
    ):
        now = timezone.now()
        created_workspaces = {}

        # Create workspaces using factory
        for ws in workspaces_to_create:
            created_at = now - timedelta(days=ws.get("days_ago", 0))
            workspace = workspace_factory(
                name=ws["name"],
                user_id=ws["user_id"],
                created_at=created_at,
            )
            created_workspaces[ws["name"]] = workspace

        # Prepare dynamic dates for query
        after_date = (now - timedelta(days=6)).isoformat().replace("+00:00", "Z")
        before_date = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
        formatted_query = query_params.format(
            after_date=after_date, before_date=before_date
        )

        url = "/workspaces/"
        if formatted_query:
            url += f"?{formatted_query}"

        response = service_user_api_client.get(url)
        assert response.status_code == 200
        data = response.json()

        # Check returned workspace names match expected
        returned_names = [ws["name"] for ws in data]
        assert set(returned_names) == set(expected_names)

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
        resp = service_user_api_client.patch(
            f"/workspaces/{user_workspace.uuid}", json={"name": "Updated"}
        )
        assert resp.status_code == 200
        user_workspace.refresh_from_db()
        assert user_workspace.name == "Updated"

    def test_update_other_workspace_denied(
        self, service_user_api_client, other_workspace
    ):
        resp = service_user_api_client.patch(
            f"/workspaces/{other_workspace.uuid}", json={"name": "Hack"}
        )
        assert resp.status_code in (403, 404)

    def test_delete_own_workspace(self, service_user_api_client, user_workspace):
        resp = service_user_api_client.delete(f"/workspaces/{user_workspace.uuid}")
        assert resp.status_code == 204
        with pytest.raises(Workspace.DoesNotExist):
            Workspace.objects.get(uuid=user_workspace.uuid)

    def test_delete_other_workspace_denied(
        self, service_user_api_client, other_workspace
    ):
        resp = service_user_api_client.delete(f"/workspaces/{other_workspace.uuid}")
        assert resp.status_code in (403, 404)

    def test_upload_image_own_workspace(
        self,
        service_user_api_client,
        user_workspace,
        temp_image_file,
    ):
        resp = service_user_api_client.post(
            f"/workspaces/{user_workspace.uuid}/upload-image",
            **{"FILES": {"image_file": temp_image_file}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["uuid"] is not None
        assert data["workspace_uuid"] == str(user_workspace.uuid)

    def test_upload_image_other_workspace_denied(
        self,
        service_user_api_client,
        other_workspace,
        temp_image_file,
    ):
        resp = service_user_api_client.post(
            f"/workspaces/{other_workspace.uuid}/upload-image",
            **{"FILES": {"image_file": temp_image_file}},
        )
        assert resp.status_code in (403, 404)


@pytest.mark.django_db
class TestWorkspaceAPIUnauthorized:
    @pytest.mark.parametrize(
        "method, url, payload",
        [
            ("get", "/workspaces/", None),
            ("post", "/workspaces/", {"name": "Fail"}),
            ("get", "/workspaces/{uuid}", None),
            ("patch", "/workspaces/{uuid}", {"name": "Fail"}),
            ("delete", "/workspaces/{uuid}", None),
        ],
    )
    def test_public_workspace_access_denied(
        self, api_client, workspace_factory, method, url, payload
    ):
        ws = workspace_factory(user_id=999)
        url = url.format(uuid=ws.uuid)

        resp = getattr(api_client, method)(url, json=payload)
        assert resp.status_code in (401, 403)

    @pytest.mark.parametrize(
        "method, url, payload",
        [
            ("get", "/internal/workspaces/", None),
            ("post", "/internal/workspaces/", {"user_id": 999, "name": "Fail"}),
            ("get", "/internal/workspaces/{uuid}", None),
            ("patch", "/internal/workspaces/{uuid}", {"name": "Fail"}),
            ("delete", "/internal/workspaces/{uuid}", None),
        ],
    )
    def test_internal_workspace_access_denied(
        self, api_client, workspace_factory, method, url, payload
    ):
        ws = workspace_factory(user_id=999)
        url = url.format(uuid=ws.uuid)

        resp = getattr(api_client, method)(url, json=payload)
        assert resp.status_code in (401, 403)
