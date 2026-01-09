import pytest
from datetime import timedelta
from django.utils import timezone
from ninja_extra.testing import TestClient

from app.api.models.task import ODMTask
from app.api.auth.nodeodm import NodeODMServiceAuth
from app.api.constants.odm import ODMTaskStatus, ODMProcessingStage
from app.api.controllers.task import TaskControllerInternal, TaskControllerPublic
from ..auth_clients import AuthStrategyEnum, AuthenticatedTestClient


@pytest.fixture
def tasks_list(workspace_factory, odm_task_factory):
    now = timezone.now()
    user_ws = workspace_factory(user_id=999)
    other_ws1 = workspace_factory(user_id=1)
    other_ws2 = workspace_factory(user_id=2)

    def create_odm_task(workspace, status, step, days_ago):
        return odm_task_factory(
            workspace=workspace,
            status=status,
            step=step,
            created_at=now - timedelta(days=days_ago),
        )

    return [
        create_odm_task(
            workspace=user_ws,
            status=ODMTaskStatus.QUEUED,
            step=ODMProcessingStage.DATASET,
            days_ago=0,
        ),
        create_odm_task(
            workspace=user_ws,
            status=ODMTaskStatus.RUNNING,
            step=ODMProcessingStage.OPENSFM,
            days_ago=1,
        ),
        create_odm_task(
            workspace=user_ws,
            status=ODMTaskStatus.COMPLETED,
            step=ODMProcessingStage.MVS_TEXTURING,
            days_ago=5,
        ),
        create_odm_task(
            workspace=user_ws,
            status=ODMTaskStatus.FAILED,
            step=ODMProcessingStage.OPENMVS,
            days_ago=10,
        ),
        create_odm_task(
            workspace=other_ws1,
            status=ODMTaskStatus.PAUSED,
            step=ODMProcessingStage.MERGE,
            days_ago=2,
        ),
        create_odm_task(
            workspace=other_ws1,
            status=ODMTaskStatus.CANCELLED,
            step=ODMProcessingStage.OPENSFM,
            days_ago=7,
        ),
        create_odm_task(
            workspace=other_ws2,
            status=ODMTaskStatus.RUNNING,
            step=ODMProcessingStage.MERGE,
            days_ago=3,
        ),
        create_odm_task(
            workspace=other_ws2,
            status=ODMTaskStatus.TIMEOUT,
            step=ODMProcessingStage.ODM_ORTHOPHOTO,
            days_ago=14,
        ),
    ]


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestTaskAPIInternal:
    @classmethod
    def setup_method(cls):
        cls.client = AuthenticatedTestClient(
            TaskControllerInternal, auth=AuthStrategyEnum.service
        )

    @pytest.mark.skip(reason="Sometimes different number of features are filtered")
    @pytest.mark.parametrize(
        "query_format, expected_count",
        [
            ("", 8),
            (f"status={ODMTaskStatus.QUEUED}", 1),
            (f"status={ODMTaskStatus.RUNNING}", 2),
            (f"status={ODMTaskStatus.COMPLETED}", 1),
            (f"step={ODMProcessingStage.DATASET}", 1),
            (f"step={ODMProcessingStage.OPENSFM}", 2),
            (f"step={ODMProcessingStage.OPENMVS}", 1),
            (f"step={ODMProcessingStage.ODM_POSTPROCESS}", 0),
            ("created_after={after}", 5),
            ("created_before={before}", 6),
            ("created_after={after}&created_before={before}", 3),
            (f"status={ODMTaskStatus.RUNNING}&created_after={{after}}", 2),
            (f"step={ODMProcessingStage.OPENSFM}&created_after={{after}}", 1),
            (f"step={ODMProcessingStage.DATASET}&created_before={{before}}", 0),
        ],
    )
    def test_list_tasks_filtering(self, tasks_list, query_format, expected_count):
        now = timezone.now()
        after_date = (now - timedelta(days=6)).isoformat().replace("+00:00", "Z")
        before_date = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
        query = query_format.format(after=after_date, before=before_date)
        url = "/" + f"?{query}" if query else ""
        resp = self.client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == expected_count, f"Failed for query: {query}"

    def test_create_task(self, mock_task_on_task_create, workspace_factory):
        ws = workspace_factory(user_id=1234)
        payload = {
            "name": "Task name",
            "options": {},
        }
        resp = self.client.post(f"/?workspace_uuid={ws.uuid}", json=payload)
        assert resp.status_code == 201

        body = resp.json()
        task = ODMTask.objects.get(uuid=body["uuid"])
        assert task.workspace.uuid == ws.uuid
        assert task.name == payload["name"]
        mock_task_on_task_create.delay.assert_called_once_with(task.uuid)

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
        "action, expected_status, expected_odm_status, mock_fixture",
        [
            ("pause", 200, ODMTaskStatus.PAUSING, "mock_task_on_task_pause"),
            ("resume", 200, ODMTaskStatus.RESUMING, "mock_task_on_task_resume"),
            ("cancel", 200, ODMTaskStatus.CANCELLING, "mock_task_on_task_cancel"),
        ],
    )
    def test_custom_actions_change_status(
        self, odm_task_factory, action, expected_status, expected_odm_status, mock_fixture, request
    ):
        mock = request.getfixturevalue(mock_fixture)
        task = odm_task_factory()
        resp = self.client.post(f"/{task.uuid}/{action}")
        assert resp.status_code == expected_status
        task.refresh_from_db()
        assert task.odm_status == expected_odm_status
        mock.delay.assert_called_once_with(task.uuid)

    @pytest.mark.parametrize(
        "odm_stage, mock_fixture",
        [
            (ODMProcessingStage.ODM_MESHING, "mock_task_on_task_nodeodm_webhook"),
            (ODMProcessingStage.ODM_POSTPROCESS, "mock_task_on_task_finish"),
        ],
    )
    def test_nodeodm_webhook_call(self, odm_task_factory, odm_stage, mock_fixture, request):
        task = odm_task_factory(step=odm_stage)
        mock = request.getfixturevalue(mock_fixture)
        signature = NodeODMServiceAuth.generate_hmac_signature(NodeODMServiceAuth.HMAC_MESSAGE)
        resp = self.client.post(f"/{task.uuid}/odmwebhook?signature={signature}")
        assert resp.status_code == 200
        mock.delay.assert_called_once_with(task.uuid)

    def test_nodeodm_webhook_call_denied(self, odm_task_factory):
        task = odm_task_factory()
        signature = NodeODMServiceAuth.generate_hmac_signature("INVALID_HMAC_MESSAGE")
        resp = self.client.post(f"/{task.uuid}/odmwebhook?signature={signature}")
        assert resp.status_code in (401, 403)


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
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

    @pytest.mark.skip(reason="Sometimes different number of features are filtered")
    @pytest.mark.parametrize(
        "query_format, expected_count",
        [
            ("", 4),
            (f"status={ODMTaskStatus.QUEUED}", 1),
            (f"status={ODMTaskStatus.RUNNING}", 1),
            (f"status={ODMTaskStatus.COMPLETED}", 1),
            (f"status={ODMTaskStatus.FAILED}", 1),
            (f"step={ODMProcessingStage.DATASET}", 1),
            (f"step={ODMProcessingStage.OPENSFM}", 1),
            (f"step={ODMProcessingStage.MVS_TEXTURING}", 1),
            (f"step={ODMProcessingStage.OPENMVS}", 1),
            ("created_after={after}", 3),
            ("created_before={before}", 2),
            ("created_after={after}&created_before={before}", 1),
            (f"status={ODMTaskStatus.RUNNING}&created_after={{after}}", 1),
            (f"step={ODMProcessingStage.OPENSFM}&created_after={{after}}", 1),
            (f"status={ODMTaskStatus.FAILED}&created_after={{after}}", 0),
        ],
    )
    def test_list_own_tasks_filtering(self, tasks_list, query_format, expected_count):
        now = timezone.now()
        after_date = (now - timedelta(days=6)).isoformat().replace("+00:00", "Z")
        before_date = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
        query = query_format.format(after=after_date, before=before_date)
        url = "/" + f"?{query}" if query else ""
        resp = self.client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == expected_count, f"Failed for query: {query}"

    def test_create_task_in_own_workspace(self, mock_task_on_task_create, user_workspace):
        payload = {
            "name": "Task name",
            "options": {},
        }
        resp = self.client.post(f"/?workspace_uuid={user_workspace.uuid}", json=payload)
        assert resp.status_code == 201
        task = ODMTask.objects.get(uuid=resp.json()["uuid"])
        assert task.workspace.user_id == 999
        assert task.name == payload["name"]
        mock_task_on_task_create.delay.assert_called_once_with(task.uuid)

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
        "action, expected_status, expected_odm_status, mock_fixture",
        [
            ("pause", 200, ODMTaskStatus.PAUSING, "mock_task_on_task_pause"),
            ("resume", 200, ODMTaskStatus.RESUMING, "mock_task_on_task_resume"),
            ("cancel", 200, ODMTaskStatus.CANCELLING, "mock_task_on_task_cancel"),
        ],
    )
    def test_custom_actions_on_own_task(
        self, user_task, action, expected_status, expected_odm_status, mock_fixture, request
    ):
        mock = request.getfixturevalue(mock_fixture)
        resp = self.client.post(f"/{user_task.uuid}/{action}")
        assert resp.status_code == expected_status
        user_task.refresh_from_db()
        assert user_task.odm_status == expected_odm_status
        mock.delay.assert_called_once_with(user_task.uuid)

    @pytest.mark.parametrize("action", ["pause", "resume", "cancel"])
    def test_action_other_task_denied(self, other_task, action):
        original_status = other_task.status
        resp = self.client.post(f"/{other_task.uuid}/{action}")
        assert resp.status_code in (403, 404)
        other_task.refresh_from_db()
        assert other_task.status == original_status
    
    def test_nodeodm_webhook_call_denied(self, odm_task_factory):
        task = odm_task_factory()
        signature = NodeODMServiceAuth.generate_hmac_signature(NodeODMServiceAuth.HMAC_MESSAGE)
        resp = self.client.post(f"/{task.uuid}/odmwebhook?signature={signature}")
        assert resp.status_code != 200


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
            ("post", "public_client", "/{uuid}/pause"),
            ("get", "internal_client", "/"),
            ("get", "internal_client", "/{uuid}"),
            ("delete", "internal_client", "/{uuid}"),
            ("post", "internal_client", "/{uuid}/pause"),
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
