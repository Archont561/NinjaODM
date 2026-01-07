import pytest
from ninja_extra.testing import TestClient
from app.api.models.task import ODMTask
from app.api.constants.odm import ODMTaskStatus
from ..auth_clients import AuthStrategyEnum, AuthenticatedTestClient
from app.api.controllers.task import TaskControllerInternal, TaskControllerPublic


@pytest.mark.django_db
class TestTaskAPIInternal:
    @classmethod
    def setup_method(cls):
        cls.client = AuthenticatedTestClient(
            TaskControllerInternal, auth=AuthStrategyEnum.service
        )

    def test_list_tasks(self, odm_task_factory, workspace_factory):
        ws1 = workspace_factory(user_id=1)
        ws2 = workspace_factory(user_id=2)
        odm_task_factory.create_batch(2, workspace=ws1)
        odm_task_factory.create_batch(3, workspace=ws2)

        resp = self.client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 5

    def test_create_task(self, workspace_factory, settings, tmp_path):
        settings.TASKS_DIR = tmp_path
        ws = workspace_factory(user_id=1234)
        payload = {
            "options": {},
        }
        resp = self.client.post(f"/?workspace_uuid={ws.uuid}", json=payload)
        assert resp.status_code == 201

        body = resp.json()
        task = ODMTask.objects.get(uuid=body["uuid"])
        assert task.workspace.uuid == ws.uuid
        assert task.task_dir.exists()

    def test_get_task(self, odm_task_factory):
        task = odm_task_factory()
        resp = self.client.get(f"/{task.uuid}")
        assert resp.status_code == 200
        assert resp.json()["uuid"] == str(task.uuid)

    @pytest.mark.parametrize("status", ODMTaskStatus.terminal_states())
    def test_delete_terminal_task(self, odm_task_factory, status):
        task = odm_task_factory(status=status)
        resp = self.client.delete(f"/{task.uuid}")
        assert resp.status_code == 204
        assert not ODMTask.objects.filter(uuid=task.uuid).exists()

    @pytest.mark.parametrize("status", ODMTaskStatus.non_terminal_states())
    def test_cannot_delete_non_terminal_task(self, odm_task_factory, status):
        task = odm_task_factory(status=status)
        resp = self.client.delete(f"/{task.uuid}")
        assert resp.status_code in (400, 403)
        assert ODMTask.objects.filter(uuid=task.pk).exists()

    @pytest.mark.parametrize(
        "action, expected_status, expected_odm_status",
        [
            ("pause", 200, ODMTaskStatus.PAUSING),
            ("resume", 200, ODMTaskStatus.RESUMING),
            ("cancel", 200, ODMTaskStatus.CANCELLING),
        ],
    )
    def test_custom_actions_change_status(
        self, odm_task_factory, action, expected_status, expected_odm_status
    ):
        task = odm_task_factory()
        resp = self.client.post(f"/{task.uuid}/{action}/")
        assert resp.status_code == expected_status
        task.refresh_from_db()
        assert task.odm_status == expected_odm_status


@pytest.mark.django_db
class TestTaskAPIPublic:
    @classmethod
    def setup_method(cls):
        cls.client = AuthenticatedTestClient(
            TaskControllerPublic, auth=AuthStrategyEnum.jwt
        )

    @pytest.fixture
    def user_workspace(self, workspace_factory):
        return workspace_factory(user_id=999, name="User WS")

    @pytest.fixture
    def other_workspace(self, workspace_factory):
        return workspace_factory(user_id=1234, name="Other WS")

    @pytest.fixture
    def user_task(self, odm_task_factory, user_workspace):
        return odm_task_factory(workspace=user_workspace)

    @pytest.fixture
    def other_task(self, odm_task_factory, other_workspace):
        return odm_task_factory(workspace=other_workspace)

    def test_list_tasks_sees_only_own(self, user_task, other_task):
        resp = self.client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["uuid"] == str(user_task.uuid)

    def test_create_task_in_own_workspace(self, user_workspace, settings, tmp_path):
        settings.TASKS_DIR = tmp_path
        payload = {"options": {}}
        resp = self.client.post(f"/?workspace_uuid={user_workspace.uuid}", json=payload)
        assert resp.status_code == 201
        task = ODMTask.objects.get(uuid=resp.json()["uuid"])
        assert task.workspace.user_id == 999
        assert task.task_dir.exists()

    def test_create_task_in_other_workspace_denied(self, other_workspace):
        payload = {"options": {}}
        resp = self.client.post(
            f"/?workspace_uuid={other_workspace.uuid}", json=payload
        )
        assert resp.status_code in (403, 404)

    def test_create_task_without_workspace_uuid_denied(self):
        payload = {"options": {}}
        resp = self.client.post("/", json=payload)
        assert resp.status_code in (403, 404)

    def test_get_own_task(self, user_task):
        resp = self.client.get(f"/{user_task.uuid}")
        assert resp.status_code == 200
        assert resp.json()["uuid"] == str(user_task.uuid)

    def test_get_other_task_denied(self, other_task):
        resp = self.client.get(f"/{other_task.uuid}")
        assert resp.status_code in (403, 404)

    @pytest.mark.parametrize("status", ODMTaskStatus.terminal_states())
    def test_delete_own_terminal_task(self, user_task, status):
        user_task.status = status
        user_task.save(update_fields=["status"])
        resp = self.client.delete(f"/{user_task.uuid}")
        assert resp.status_code == 204
        assert not ODMTask.objects.filter(uuid=user_task.uuid).exists()

    @pytest.mark.parametrize("status", ODMTaskStatus.non_terminal_states())
    def test_cannot_delete_own_non_terminal_task(self, user_task, status):
        user_task.status = status
        user_task.save(update_fields=["status"])
        resp = self.client.delete(f"/{user_task.uuid}")
        assert resp.status_code in (400, 403)
        assert ODMTask.objects.filter(uuid=user_task.uuid).exists()

    @pytest.mark.parametrize(
        "action, expected_status, expected_odm_status",
        [
            ("pause", 200, ODMTaskStatus.PAUSING),
            ("resume", 200, ODMTaskStatus.RESUMING),
            ("cancel", 200, ODMTaskStatus.CANCELLING),
        ],
    )
    def test_custom_actions_on_own_task(
        self, user_task, action, expected_status, expected_odm_status
    ):
        resp = self.client.post(f"/{user_task.uuid}/{action}/")
        assert resp.status_code == expected_status
        user_task.refresh_from_db()
        assert user_task.odm_status == expected_odm_status

    @pytest.mark.parametrize("action", ["pause", "resume", "cancel"])
    def test_action_other_task_denied(self, other_task, action):
        original_status = other_task.status
        resp = self.client.post(f"/{other_task.uuid}/{action}/")
        assert resp.status_code in (403, 404)
        other_task.refresh_from_db()
        assert other_task.status == original_status


@pytest.mark.django_db
class TestTaskAPIUnauthorized:
    @classmethod
    def setup_method(cls):
        cls.public_client = TestClient(TaskControllerPublic)
        cls.internal_client = TestClient(TaskControllerInternal)
        cls.user_client = AuthenticatedTestClient(
            TaskControllerInternal, auth=AuthStrategyEnum.jwt
        )

    @pytest.mark.parametrize(
        "method, client_type, url_template",
        [
            ("get", "public_client", "/"),
            ("get", "public_client", "/{uuid}"),
            ("post", "public_client", "/{uuid}/pause/"),
            ("get", "internal_client", "/"),
            ("get", "internal_client", "/{uuid}"),
            ("delete", "internal_client", "/{uuid}"),
            ("post", "internal_client", "/{uuid}/pause/"),
            ("get", "user_client", "/"),
            ("get", "user_client", "/{uuid}"),
            ("delete", "user_client", "/{uuid}"),
        ],
    )
    def test_access_denied(self, odm_task_factory, method, client_type, url_template):
        task = odm_task_factory()
        client = getattr(self, client_type)
        url = url_template.format(uuid=task.uuid)
        resp = getattr(client, method)(url)
        assert resp.status_code in (401, 403)

        if method == "delete":
            assert ODMTask.objects.filter(pk=task.pk).exists()
