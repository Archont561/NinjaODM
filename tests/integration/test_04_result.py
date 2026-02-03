import pytest
from datetime import timedelta
from django.utils import timezone
from ninja_extra.testing import TestClient

from app.api.models.result import ODMTaskResult
from app.api.models.workspace import Workspace
from app.api.constants.odm import ODMTaskResultType
from app.api.constants.token import ShareToken
from app.api.controllers.result import ResultControllerInternal, ResultControllerPublic
from tests.utils import APITestSuite, AuthStrategyEnum, AuthenticatedTestClient

# =========================================================================
# FIXTURES
# =========================================================================

# -------------------------
# Clients
# -------------------------


@pytest.fixture
def result_public_client():
    """JWT authenticated client for public Result API."""
    return AuthenticatedTestClient(ResultControllerPublic, auth=AuthStrategyEnum.jwt)


@pytest.fixture
def result_internal_client():
    """Service authenticated client for internal Result API."""
    return AuthenticatedTestClient(
        ResultControllerInternal, auth=AuthStrategyEnum.service
    )


@pytest.fixture
def result_anon_public_client():
    """Unauthenticated client for public Result API."""
    return TestClient(ResultControllerPublic)


@pytest.fixture
def result_anon_internal_client():
    """Unauthenticated client for internal Result API."""
    return TestClient(ResultControllerInternal)


@pytest.fixture
def result_jwt_internal_client():
    """JWT client for internal Result API (should be denied)."""
    return AuthenticatedTestClient(ResultControllerInternal, auth=AuthStrategyEnum.jwt)


# -------------------------
# Workspace Fixtures
# -------------------------


@pytest.fixture
def user_result_workspace(workspace_factory):
    """Workspace owned by user_999 for result tests."""
    return workspace_factory(user_id="user_999")


@pytest.fixture
def other_result_workspace(workspace_factory):
    """Workspace owned by another user for result tests."""
    return workspace_factory(user_id="user_other")


# -------------------------
# Result Factories
# -------------------------


@pytest.fixture
def user_result_factory(
    odm_task_result_factory, user_result_workspace, image_file_factory
):
    """Factory for results with actual file in user_999's workspace."""

    def factory(**kwargs):
        file_obj = image_file_factory()
        data = {"workspace": user_result_workspace, "file": file_obj, **kwargs}
        return odm_task_result_factory(**data)

    return factory


@pytest.fixture
def other_result_factory(user_result_factory, other_result_workspace):
    """Factory for results with actual file in other user's workspace."""

    def factory(**kwargs):
        return user_result_factory(workspace=other_result_workspace)

    return factory


@pytest.fixture
def shared_result_factory(user_result_factory):
    """Factory for shared result with token in URL."""

    def factory(**kwargs):
        result = user_result_factory()
        result._share_token = str(ShareToken.for_result(result))
        return result

    return factory


@pytest.fixture
def wrong_shared_result_factory(user_result_factory, other_result_factory):
    """Factory for result with wrong share token."""

    def factory(**kwargs):
        user_result = user_result_factory()
        other_result = other_result_factory()
        user_result._share_token = str(ShareToken.for_result(other_result))
        return user_result

    return factory


# -------------------------
# Result List Factory
# -------------------------


@pytest.fixture
def result_list_factory(workspace_factory, odm_task_result_factory):
    """Factory for result list (filtering tests)."""

    def factory():
        # Clear existing data
        ODMTaskResult.objects.all().delete()
        Workspace.objects.all().delete()

        now = timezone.now()
        user_ws = workspace_factory(user_id="user_999")
        other_ws1 = workspace_factory(user_id="user_1")
        other_ws2 = workspace_factory(user_id="user_2")

        def create_result(workspace, r_type, days_ago):
            return odm_task_result_factory(
                workspace=workspace,
                result_type=r_type,
                created_at=now - timedelta(days=days_ago),
            )

        return {
            "user_ws": user_ws,
            "other_ws1": other_ws1,
            "other_ws2": other_ws2,
            "results": [
                create_result(user_ws, ODMTaskResultType.ORTHOPHOTO_GEOTIFF, 7),
                create_result(user_ws, ODMTaskResultType.ORTHOPHOTO_GEOTIFF, 3),
                create_result(user_ws, ODMTaskResultType.POINT_CLOUD_PLY, 3),
                create_result(user_ws, ODMTaskResultType.POINT_CLOUD_PLY, 1),
                create_result(other_ws1, ODMTaskResultType.ORTHOPHOTO_GEOTIFF, 3),
                create_result(other_ws2, ODMTaskResultType.DTM, 1),
                create_result(other_ws2, ODMTaskResultType.REPORT, 8),
            ],
        }

    yield factory
    ODMTaskResult.objects.all().delete()


# -------------------------
# List Queries
# -------------------------


@pytest.fixture
def internal_result_list_queries(result_list_factory):
    """Queries for internal Result API (sees all 7 results)."""
    data = result_list_factory()
    now = timezone.now()
    after = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
    before = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    ws1_uuid = str(data["user_ws"].uuid)
    ws2_uuid = str(data["other_ws1"].uuid)
    ws3_uuid = str(data["other_ws2"].uuid)

    return [
        {"params": {}, "expected_count": 7},
        {
            "params": {"result_type": ODMTaskResultType.ORTHOPHOTO_GEOTIFF},
            "expected_count": 3,
        },
        {
            "params": {"result_type": ODMTaskResultType.POINT_CLOUD_PLY},
            "expected_count": 2,
        },
        {"params": {"result_type": ODMTaskResultType.DTM}, "expected_count": 1},
        {"params": {"created_after": after}, "expected_count": 5},
        {"params": {"created_before": before}, "expected_count": 5},
        {
            "params": {
                "result_type": ODMTaskResultType.ORTHOPHOTO_GEOTIFF,
                "created_after": after,
            },
            "expected_count": 2,
        },
        {
            "params": {
                "result_type": ODMTaskResultType.POINT_CLOUD_PLY,
                "created_before": before,
            },
            "expected_count": 1,
        },
        {"params": {"workspace_uuid": ws1_uuid}, "expected_count": 4},
        {"params": {"workspace_uuid": ws2_uuid}, "expected_count": 1},
        {"params": {"workspace_uuid": ws3_uuid}, "expected_count": 2},
        {
            "params": {
                "workspace_uuid": ws1_uuid,
                "result_type": ODMTaskResultType.POINT_CLOUD_PLY,
            },
            "expected_count": 2,
        },
    ]


@pytest.fixture
def public_result_list_queries(result_list_factory):
    """Queries for public Result API (user_999 sees only 4 results)."""
    data = result_list_factory()
    now = timezone.now()
    after = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
    before = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    ws_own_uuid = str(data["user_ws"].uuid)
    ws_other_uuid = str(data["other_ws1"].uuid)

    return [
        {"params": {}, "expected_count": 4},
        {
            "params": {"result_type": ODMTaskResultType.ORTHOPHOTO_GEOTIFF},
            "expected_count": 2,
        },
        {
            "params": {"result_type": ODMTaskResultType.POINT_CLOUD_PLY},
            "expected_count": 2,
        },
        {"params": {"result_type": ODMTaskResultType.DTM}, "expected_count": 0},
        {"params": {"created_after": after}, "expected_count": 3},
        {"params": {"created_before": before}, "expected_count": 3},
        {
            "params": {
                "result_type": ODMTaskResultType.ORTHOPHOTO_GEOTIFF,
                "created_after": after,
            },
            "expected_count": 1,
        },
        {
            "params": {
                "result_type": ODMTaskResultType.POINT_CLOUD_PLY,
                "created_before": before,
            },
            "expected_count": 1,
        },
        {"params": {"workspace_uuid": ws_own_uuid}, "expected_count": 4},
        {"params": {"workspace_uuid": ws_other_uuid}, "expected_count": 0},
    ]


# -------------------------
# Assertions
# -------------------------


@pytest.fixture
def assert_result_deleted():
    """Assertion that result is deleted."""

    def assertion(obj, resp):
        assert resp.status_code == 204
        assert not ODMTaskResult.objects.filter(pk=obj.pk).exists()
        return True

    return assertion


@pytest.fixture
def assert_result_download(image_file_factory):
    """Assertion for result download."""

    def assertion(obj, resp):
        assert resp.status_code == 200
        assert "image/jpeg" in resp.headers.get("Content-Type", "")
        assert "attachment" in resp.headers.get("Content-Disposition", "")

        simple_image = image_file_factory()
        assert resp.content == simple_image.read()
        return True

    return assertion


@pytest.fixture
def assert_share_token():
    """Assertion for share token response."""

    def assertion(obj, resp):
        assert resp.status_code == 200
        data = resp.json()
        assert "share_api_key" in data

        # Validate token claims
        token = ShareToken(data["share_api_key"], verify=False)
        assert token["token_type"] == "share"
        assert token["result_uuid"] == str(obj.uuid)
        return True

    return assertion


# =========================================================================
# TEST SUITE
# =========================================================================


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
@pytest.mark.freeze_time("2026-01-20 12:00:00")
class TestResultAPI(APITestSuite):
    """
    Result API tests.
    """

    tests = {
        # ===== DEFAULTS =====
        "model": ODMTaskResult,
        "endpoint": "/",
        "factory": "user_result_factory",
        "client": "result_public_client",
        # ===== CRUD =====
        "cruds": {
            # Note: Create is not exposed via API
            # ----- GET -----
            "get": {
                "scenarios": [
                    {
                        "name": "jwt_own",
                        "assert": lambda s, obj, resp: str(obj.uuid)
                        == resp.json()["uuid"],
                    },
                    {
                        "name": "jwt_other_denied",
                        "factory": "other_result_factory",
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                    {
                        "name": "anon_public_denied",
                        "client": "result_anon_public_client",
                        "expected_status": 401,
                        "access_denied": True,
                    },
                ],
            },
            # ----- DELETE -----
            "delete": {
                "scenarios": [
                    {
                        "name": "jwt_own",
                        "assert": "assert_result_deleted",
                    },
                    {
                        "name": "jwt_other_denied",
                        "factory": "other_result_factory",
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                    {
                        "name": "anon_public_denied",
                        "client": "result_anon_public_client",
                        "expected_status": 401,
                        "access_denied": True,
                    },
                ],
            },
        },
        # ===== ACTIONS =====
        "actions": {
            # ----- Download -----
            "download": {
                "url": lambda s, obj: f"/{obj.uuid}/download",
                "method": "get",
                "scenarios": [
                    {
                        "name": "jwt_own",
                        "assert": "assert_result_download",
                    },
                    {
                        "name": "jwt_other_denied",
                        "factory": "other_result_factory",
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                ],
            },
            # ----- Share Token -----
            "share": {
                "url": lambda s, obj: f"/{obj.uuid}/share",
                "method": "get",
                "scenarios": [
                    {
                        "name": "jwt_own",
                        "assert": "assert_share_token",
                    },
                    {
                        "name": "jwt_other_denied",
                        "factory": "other_result_factory",
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                ],
            },
            # ----- Shared Download -----
            "shared_download": {
                "url": lambda s, obj: f"/{obj.uuid}/shared?api_key={obj._share_token}",
                "method": "get",
                "scenarios": [
                    {
                        "name": "anon_valid_token",
                        "client": "result_anon_public_client",
                        "factory": "shared_result_factory",
                        "assert": "assert_result_download",
                    },
                    {
                        "name": "anon_wrong_token_denied",
                        "client": "result_anon_public_client",
                        "factory": "wrong_shared_result_factory",
                        "expected_status": [403, 404],
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
                    "client": "result_internal_client",
                    "queries": "internal_result_list_queries",
                },
                {
                    "name": "public_jwt",
                    "queries": "public_result_list_queries",
                },
                {
                    "name": "anon_denied",
                    "client": "result_anon_public_client",
                    "queries": [{"params": {}, "expected_status": 401}],
                },
                {
                    "name": "jwt_internal_denied",
                    "client": "result_jwt_internal_client",
                    "queries": [{"params": {}, "expected_status": [401, 403]}],
                },
            ],
        },
    }
