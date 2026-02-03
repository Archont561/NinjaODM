import pytest
from uuid import uuid4
from datetime import timedelta
from django.utils import timezone
from ninja_extra.testing import TestClient

from app.api.models.task import ODMTask
from app.api.models.workspace import Workspace
from app.api.auth.nodeodm import NodeODMServiceAuth
from app.api.constants.odm import ODMTaskStatus, ODMProcessingStage, NodeODMTaskStatus
from app.api.controllers.task import TaskControllerInternal, TaskControllerPublic
from tests.utils import APITestSuite, AuthStrategyEnum, AuthenticatedTestClient

# =========================================================================
# CLIENT FIXTURES
# =========================================================================


@pytest.fixture
def task_public_client():
    return AuthenticatedTestClient(TaskControllerPublic, auth=AuthStrategyEnum.jwt)


@pytest.fixture
def task_internal_client():
    return AuthenticatedTestClient(
        TaskControllerInternal, auth=AuthStrategyEnum.service
    )


@pytest.fixture
def task_anon_public_client():
    return TestClient(TaskControllerPublic)


@pytest.fixture
def task_anon_internal_client():
    return TestClient(TaskControllerInternal)


@pytest.fixture
def task_jwt_internal_client():
    return AuthenticatedTestClient(TaskControllerInternal, auth=AuthStrategyEnum.jwt)


# =========================================================================
# DATA FACTORY FIXTURES
# =========================================================================


@pytest.fixture
def user_task_workspace(workspace_factory, image_factory):
    ws = workspace_factory(user_id="user_999", name="User WS")
    image_factory(workspace=ws)
    return ws


@pytest.fixture
def user_task_workspace_no_images(workspace_factory):
    ws = workspace_factory(user_id="user_999", name="User WS (no images)")
    return ws


@pytest.fixture
def other_task_workspace(workspace_factory):
    return workspace_factory(user_id="user_1234", name="Other WS")


@pytest.fixture
def user_task_factory(odm_task_factory, user_task_workspace):
    def factory(**kwargs):
        return odm_task_factory(workspace=user_task_workspace, **kwargs)

    return factory


@pytest.fixture
def other_task_factory(odm_task_factory, other_task_workspace):
    def factory(**kwargs):
        return odm_task_factory(workspace=other_task_workspace, **kwargs)

    return factory


@pytest.fixture
def user_terminal_task_factory(odm_task_factory, user_task_workspace):
    def factory(**kwargs):
        kwargs.setdefault("status", ODMTaskStatus.COMPLETED)
        return odm_task_factory(workspace=user_task_workspace, **kwargs)

    return factory


@pytest.fixture
def user_non_terminal_task_factory(odm_task_factory, user_task_workspace):
    def factory(**kwargs):
        kwargs.setdefault("status", ODMTaskStatus.RUNNING)
        return odm_task_factory(workspace=user_task_workspace, **kwargs)

    return factory


@pytest.fixture
def webhook_task_meshing_factory(odm_task_factory, workspace_factory):
    def factory(**kwargs):
        ws = workspace_factory()
        return odm_task_factory(
            workspace=ws, step=ODMProcessingStage.ODM_MESHING, **kwargs
        )

    return factory


@pytest.fixture
def webhook_task_postprocess_factory(odm_task_factory, workspace_factory):
    def factory(**kwargs):
        ws = workspace_factory()
        return odm_task_factory(
            workspace=ws, step=ODMProcessingStage.ODM_POSTPROCESS, **kwargs
        )

    return factory


@pytest.fixture
def any_task_factory(odm_task_factory, workspace_factory):
    def factory(**kwargs):
        return odm_task_factory(workspace=workspace_factory(), **kwargs)

    return factory


# =========================================================================
# WEBHOOK DATA FIXTURES
# =========================================================================


@pytest.fixture
def nodeodm_webhook_payload():
    return {
        "uuid": str(uuid4()),
        "name": "test-task",
        "dateCreated": 1700000000,
        "processingTime": 123.45,
        "status": {"code": NodeODMTaskStatus.COMPLETED},
        "options": {"dsm": True},
        "imagesCount": 42,
        "progress": 100,
    }


@pytest.fixture
def valid_nodeodm_signature():
    return NodeODMServiceAuth.generate_hmac_signature(NodeODMServiceAuth.HMAC_MESSAGE)


@pytest.fixture
def invalid_nodeodm_signature():
    return NodeODMServiceAuth.generate_hmac_signature("INVALID_HMAC_MESSAGE")


# =========================================================================
# ASSERTION FIXTURES
# =========================================================================


@pytest.fixture
def assert_task_created(mock_task_on_task_create):
    def assertion(obj, payload):
        assert obj.name == payload.get("name")
        # FIX: Check .delay()
        mock_task_on_task_create.delay.assert_called_with(obj.uuid)
        return True

    return assertion


@pytest.fixture
def assert_task_paused(mock_task_on_task_pause):
    def assertion(obj, resp):
        assert resp.status_code == 200
        obj.refresh_from_db()
        assert obj.odm_status == ODMTaskStatus.PAUSING
        mock_task_on_task_pause.delay.assert_called_with(obj.uuid)
        return True

    return assertion


@pytest.fixture
def assert_task_resumed(mock_task_on_task_resume):
    def assertion(obj, resp):
        assert resp.status_code == 200
        obj.refresh_from_db()
        assert obj.odm_status == ODMTaskStatus.RESUMING
        mock_task_on_task_resume.delay.assert_called_with(obj.uuid)
        return True

    return assertion


@pytest.fixture
def assert_task_cancelled(mock_task_on_task_cancel):
    def assertion(obj, resp):
        assert resp.status_code == 200
        obj.refresh_from_db()
        assert obj.odm_status == ODMTaskStatus.CANCELLING
        mock_task_on_task_cancel.delay.assert_called_with(obj.uuid)
        return True

    return assertion


@pytest.fixture
def assert_webhook_processed(mock_task_on_task_nodeodm_webhook):
    def assertion(obj, resp):
        assert resp.status_code == 200
        if mock_task_on_task_nodeodm_webhook.called:
            mock_task_on_task_nodeodm_webhook.delay.assert_called()
        return True

    return assertion


@pytest.fixture
def assert_task_finished(mock_task_on_task_finish):
    def assertion(obj, resp):
        assert resp.status_code == 200
        mock_task_on_task_finish.delay.assert_called_with(obj.uuid)
        return True

    return assertion


@pytest.fixture
def assert_task_failed(mock_task_on_task_failure):
    def assertion(obj, resp):
        assert resp.status_code == 200
        mock_task_on_task_failure.delay.assert_called_with(obj.uuid)
        return True

    return assertion


# =========================================================================
# LIST FILTERING FIXTURES
# =========================================================================


@pytest.fixture
def task_list_factory(workspace_factory, odm_task_factory):
    """Factory for task list (filtering tests)."""

    def factory():
        # Clear existing data
        ODMTask.objects.all().delete()
        Workspace.objects.all().delete()

        now = timezone.now()
        user_ws = workspace_factory(user_id="user_999")
        other_ws1 = workspace_factory(user_id="user_1")
        other_ws2 = workspace_factory(user_id="user_2")

        def create_task(workspace, status, step, days_ago):
            return odm_task_factory(
                workspace=workspace,
                status=status,
                step=step,
                created_at=now - timedelta(days=days_ago),
            )

        tasks = [
            create_task(user_ws, ODMTaskStatus.QUEUED, ODMProcessingStage.DATASET, 0),
            create_task(user_ws, ODMTaskStatus.RUNNING, ODMProcessingStage.OPENSFM, 1),
            create_task(
                user_ws, ODMTaskStatus.COMPLETED, ODMProcessingStage.MVS_TEXTURING, 5
            ),
            create_task(user_ws, ODMTaskStatus.FAILED, ODMProcessingStage.OPENMVS, 10),
            create_task(other_ws1, ODMTaskStatus.PAUSED, ODMProcessingStage.MERGE, 2),
            create_task(
                other_ws1, ODMTaskStatus.CANCELLED, ODMProcessingStage.OPENSFM, 7
            ),
            create_task(other_ws2, ODMTaskStatus.RUNNING, ODMProcessingStage.MERGE, 3),
            create_task(
                other_ws2, ODMTaskStatus.PAUSING, ODMProcessingStage.ODM_ORTHOPHOTO, 14
            ),
        ]

        return {
            "user_ws": user_ws,
            "other_ws1": other_ws1,
            "other_ws2": other_ws2,
            "tasks": tasks,
        }

    yield factory
    ODMTask.objects.all().delete()


@pytest.fixture
def public_task_list_queries(task_list_factory):
    data = task_list_factory()
    now = timezone.now()
    after = (now - timedelta(days=6)).isoformat().replace("+00:00", "Z")
    before = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    ws_own_uuid = str(data["user_ws"].uuid)
    ws_other_uuid = str(data["other_ws1"].uuid)

    return [
        {"params": {}, "expected_count": 4},
        {"params": {"status": ODMTaskStatus.QUEUED}, "expected_count": 1},
        {"params": {"status": ODMTaskStatus.RUNNING}, "expected_count": 1},
        {"params": {"status": ODMTaskStatus.COMPLETED}, "expected_count": 1},
        {"params": {"status": ODMTaskStatus.FAILED}, "expected_count": 1},
        {"params": {"step": ODMProcessingStage.DATASET}, "expected_count": 1},
        {"params": {"step": ODMProcessingStage.OPENSFM}, "expected_count": 1},
        {"params": {"step": ODMProcessingStage.MVS_TEXTURING}, "expected_count": 1},
        {"params": {"step": ODMProcessingStage.OPENMVS}, "expected_count": 1},
        {"params": {"created_after": after}, "expected_count": 3},
        {"params": {"created_before": before}, "expected_count": 2},
        {
            "params": {"created_after": after, "created_before": before},
            "expected_count": 1,
        },
        {
            "params": {"status": ODMTaskStatus.RUNNING, "created_after": after},
            "expected_count": 1,
        },
        {
            "params": {"step": ODMProcessingStage.OPENSFM, "created_after": after},
            "expected_count": 1,
        },
        {
            "params": {"status": ODMTaskStatus.FAILED, "created_after": after},
            "expected_count": 0,
        },
        {"params": {"workspace_uuid": ws_own_uuid}, "expected_count": 4},
        {"params": {"workspace_uuid": ws_other_uuid}, "expected_count": 0},
    ]


@pytest.fixture
def internal_task_list_queries(task_list_factory):
    """Queries for internal Task API (sees all 8 tasks)."""
    data = task_list_factory()
    now = timezone.now()
    after = (now - timedelta(days=6)).isoformat().replace("+00:00", "Z")
    before = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    ws1_uuid = str(data["user_ws"].uuid)
    ws2_uuid = str(data["other_ws1"].uuid)
    ws3_uuid = str(data["other_ws2"].uuid)

    return [
        {"params": {}, "expected_count": 8},
        {"params": {"status": ODMTaskStatus.QUEUED}, "expected_count": 1},
        {"params": {"status": ODMTaskStatus.RUNNING}, "expected_count": 2},
        {"params": {"status": ODMTaskStatus.COMPLETED}, "expected_count": 1},
        {"params": {"step": ODMProcessingStage.DATASET}, "expected_count": 1},
        {"params": {"step": ODMProcessingStage.OPENSFM}, "expected_count": 2},
        {"params": {"step": ODMProcessingStage.OPENMVS}, "expected_count": 1},
        {"params": {"step": ODMProcessingStage.ODM_POSTPROCESS}, "expected_count": 0},
        {"params": {"created_after": after}, "expected_count": 5},
        {"params": {"created_before": before}, "expected_count": 6},
        {
            "params": {"created_after": after, "created_before": before},
            "expected_count": 3,
        },
        {
            "params": {"status": ODMTaskStatus.RUNNING, "created_after": after},
            "expected_count": 2,
        },
        {
            "params": {"step": ODMProcessingStage.OPENSFM, "created_after": after},
            "expected_count": 1,
        },
        {
            "params": {"step": ODMProcessingStage.DATASET, "created_before": before},
            "expected_count": 0,
        },
        {"params": {"workspace_uuid": ws1_uuid}, "expected_count": 4},
        {"params": {"workspace_uuid": ws2_uuid}, "expected_count": 2},
        {"params": {"workspace_uuid": ws3_uuid}, "expected_count": 2},
        {
            "params": {"workspace_uuid": ws1_uuid, "status": ODMTaskStatus.RUNNING},
            "expected_count": 1,
        },
    ]


# =========================================================================
# TEST SUITE
# =========================================================================


@pytest.mark.django_db
@pytest.mark.freeze_time("2026-01-20 12:00:00")
@pytest.mark.usefixtures(
    "mock_task_on_task_create",
    "mock_task_on_task_pause",
    "mock_task_on_task_resume",
    "mock_task_on_task_cancel",
    "mock_task_on_task_nodeodm_webhook",
    "mock_task_on_task_finish",
    "mock_task_on_task_failure",
    "mock_redis",
)
class TestTaskAPI(APITestSuite):
    """
    Task API tests.
    """

    tests = {
        # ===== DEFAULTS =====
        "model": ODMTask,
        "endpoint": "/",
        "factory": "user_task_factory",
        "client": "task_public_client",
        # ===== CRUD =====
        "cruds": {
            # ----- CREATE -----
            "create": {
                "expected_status": 201,
                "scenarios": [
                    {
                        "name": "jwt_own_workspace",
                        "payload": lambda s: {
                            "workspace_uuid": s.fixture("user_task_workspace").uuid,
                            "name": "User Task",
                            "quality": "low",
                        },
                        "assert": "assert_task_created",
                    },
                    {
                        "name": "jwt_workspace_without_images_denied",
                        "payload": lambda s: {
                            "workspace_uuid": s.fixture(
                                "user_task_workspace_no_images"
                            ).uuid,
                            "name": "Task without images",
                            "quality": "low",
                        },
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                    {
                        "name": "jwt_other_workspace_denied",
                        "payload": lambda s: {
                            "workspace_uuid": s.fixture("other_task_workspace").uuid,
                            "name": "Forbidden Task",
                            "quality": "low",
                        },
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                    {
                        "name": "anon_public_denied",
                        "client": "task_anon_public_client",
                        "payload": lambda s: {
                            "workspace_uuid": s.fixture("user_task_workspace").uuid,
                            "name": "Anon Task",
                            "quality": "low",
                        },
                        "expected_status": 401,
                        "access_denied": True,
                    },
                ],
            },
            # ----- GET -----
            "get": {
                "scenarios": [
                    {
                        "name": "jwt_own",
                        "assert": lambda s, obj, resp: resp.json()["uuid"]
                        == str(obj.uuid),
                    },
                    {
                        "name": "jwt_other_denied",
                        "factory": "other_task_factory",
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                ],
            },
            # ----- DELETE -----
            "delete": {
                "scenarios": [
                    {
                        "name": "jwt_own_terminal",
                        "factory": "user_terminal_task_factory",
                    },
                    {
                        "name": "jwt_own_non_terminal_denied",
                        "factory": "user_non_terminal_task_factory",
                        "expected_status": 409,
                        "access_denied": True,
                    },
                ],
            },
        },
        # ===== ACTIONS =====
        "actions": {
            "pause": {
                "url": lambda s, obj: f"/{obj.uuid}/pause",
                "method": "post",
                "scenarios": [
                    {"name": "jwt_own", "assert": "assert_task_paused"},
                    {
                        "name": "jwt_other_denied",
                        "factory": "other_task_factory",
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                ],
            },
            "resume": {
                "url": lambda s, obj: f"/{obj.uuid}/resume",
                "method": "post",
                "scenarios": [
                    {"name": "jwt_own", "assert": "assert_task_resumed"},
                ],
            },
            "cancel": {
                "url": lambda s, obj: f"/{obj.uuid}/cancel",
                "method": "post",
                "scenarios": [
                    {"name": "jwt_own", "assert": "assert_task_cancelled"},
                ],
            },
            # ----- NodeODM Webhook -----
            "webhook_postprocess_completed": {
                "url": lambda s,
                obj: f"/{obj.uuid}/webhooks/odm?signature={s.fixture('valid_nodeodm_signature')}",
                "method": "post",
                "payload": lambda s: {
                    **s.fixture("nodeodm_webhook_payload"),
                    "status": {"code": NodeODMTaskStatus.COMPLETED},
                },
                "scenarios": [
                    {
                        "name": "task_finished",
                        "client": "task_internal_client",
                        "factory": "webhook_task_postprocess_factory",
                        "assert": "assert_task_finished",
                    },
                ],
            },
            "webhook_postprocess_failed": {
                "url": lambda s,
                obj: f"/{obj.uuid}/webhooks/odm?signature={s.fixture('valid_nodeodm_signature')}",
                "method": "post",
                "payload": lambda s: {
                    **s.fixture("nodeodm_webhook_payload"),
                    "status": {"code": NodeODMTaskStatus.FAILED},
                },
                "scenarios": [
                    {
                        "name": "task_failed",
                        "client": "task_internal_client",
                        "factory": "webhook_task_postprocess_factory",
                        "assert": "assert_task_failed",
                    },
                ],
            },
            "webhook_invalid_signature": {
                "url": lambda s,
                obj: f"/{obj.uuid}/webhooks/odm?signature={s.fixture('invalid_nodeodm_signature')}",
                "method": "post",
                "payload": lambda s: s.fixture("nodeodm_webhook_payload"),
                "scenarios": [
                    {
                        "name": "invalid_signature_denied",
                        "client": "task_internal_client",
                        "factory": "any_task_factory",
                        "expected_status": [401, 403],
                        "access_denied": True,
                    },
                ],
            },
        },
        # ===== LIST =====
        "list": {
            "url": "/",
            "method": "get",
            "scenarios": [
                {
                    "name": "internal",
                    "client": "task_internal_client",
                    "queries": "internal_task_list_queries",
                },
                {
                    "name": "public_jwt",
                    "queries": "public_task_list_queries",
                },
                {
                    "name": "anon_denied",
                    "client": "task_anon_public_client",
                    "queries": [{"params": {}, "expected_status": 401}],
                },
            ],
        },
    }
