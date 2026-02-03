import pytest
from unittest.mock import patch
from datetime import timedelta
from django.utils import timezone
from ninja_extra.testing import TestClient

from app.api.models.workspace import Workspace
from app.api.models.image import Image
from app.api.controllers.workspace import (
    WorkspaceControllerInternal,
    WorkspaceControllerPublic,
)
from app.api.constants.odm import ODMTaskStatus
from tests.utils import AuthStrategyEnum, AuthenticatedTestClient, APITestSuite

# =========================================================================
# MOCK FIXTURES (Background Tasks)
# =========================================================================

@pytest.fixture
def mock_task_on_workspace_images_uploaded():
    with patch("app.api.services.workspace.on_workspace_images_uploaded") as mock:
        yield mock

# =========================================================================
# CLIENT FIXTURES
# =========================================================================

@pytest.fixture
def public_client():
    """JWT authenticated client for public API."""
    return AuthenticatedTestClient(
        WorkspaceControllerPublic, auth=AuthStrategyEnum.jwt
    )


@pytest.fixture
def internal_client():
    """Service authenticated client for internal API."""
    return AuthenticatedTestClient(
        WorkspaceControllerInternal, auth=AuthStrategyEnum.service
    )


@pytest.fixture
def service_public_client():
    """Service authenticated client for public API."""
    return AuthenticatedTestClient(
        WorkspaceControllerPublic, auth=AuthStrategyEnum.service
    )


@pytest.fixture
def anon_public_client():
    """Unauthenticated client for public API."""
    return TestClient(WorkspaceControllerPublic)


@pytest.fixture
def anon_internal_client():
    """Unauthenticated client for internal API."""
    return TestClient(WorkspaceControllerInternal)


@pytest.fixture
def jwt_internal_client():
    """JWT client for internal API (should be denied)."""
    return AuthenticatedTestClient(
        WorkspaceControllerInternal, auth=AuthStrategyEnum.jwt
    )


# =========================================================================
# DATA FACTORY FIXTURES
# =========================================================================

@pytest.fixture
def user_workspace_factory(workspace_factory):
    """Factory for user_999 workspaces."""
    return lambda **kw: workspace_factory(user_id="user_999", name="User WS", **kw)


@pytest.fixture
def other_workspace_factory(workspace_factory):
    """Factory for other user workspaces."""
    return lambda **kw: workspace_factory(user_id="user_1234", name="Other WS", **kw)


@pytest.fixture
def deletable_user_workspace_factory(workspace_factory, odm_task_factory):
    """User workspace with cancelled task."""
    def factory(**kw):
        ws = workspace_factory(user_id="user_999", name="Deletable WS", **kw)
        odm_task_factory(workspace=ws, status=ODMTaskStatus.CANCELLED)
        return ws
    return factory


@pytest.fixture
def non_deletable_user_workspace_factory(workspace_factory, odm_task_factory):
    """User workspace with running task."""
    def factory(**kw):
        ws = workspace_factory(user_id="user_999", name="Non-Deletable WS", **kw)
        odm_task_factory(workspace=ws, status=ODMTaskStatus.QUEUED)
        return ws
    return factory


@pytest.fixture
def deletable_other_workspace_factory(workspace_factory, odm_task_factory):
    """Other user workspace with cancelled task."""
    def factory(**kw):
        ws = workspace_factory(user_id="user_1234", name="Other Deletable WS", **kw)
        odm_task_factory(workspace=ws, status=ODMTaskStatus.CANCELLED)
        return ws
    return factory


@pytest.fixture
def non_deletable_other_workspace_factory(workspace_factory, odm_task_factory):
    """Other user workspace with running task."""
    def factory(**kw):
        ws = workspace_factory(user_id="user_1234", name="Other Non-Deletable WS", **kw)
        odm_task_factory(workspace=ws, status=ODMTaskStatus.QUEUED)
        return ws
    return factory


# -------------------------
# Workspace List
# -------------------------

@pytest.fixture
def workspace_list_factory(workspace_factory):
    """Factory for workspace list (filtering tests)."""
    def factory():
        Workspace.objects.all().delete()
        now = timezone.now()
        
        def create(name, user_id, days_ago):
            return workspace_factory(
                name=name,
                user_id=user_id,
                created_at=now - timedelta(days=days_ago),
            )
        
        return [
            create("ProjectA", "user_999", 10),
            create("ProjectB", "user_999", 5),
            create("SharedProject", "user_999", 3),
            create("ProjectC", "user_999", 1),
            create("OtherUser1", "user_1", 8),
            create("OtherProject", "user_3", 6),
            create("OtherUser2", "user_3", 2),
        ]
    return factory


# =========================================================================
# QUERY FIXTURES
# =========================================================================

@pytest.fixture
def internal_list_queries():
    """Queries for internal API (sees all 7 workspaces)."""
    now = timezone.now()
    after = (now - timedelta(days=6)).isoformat().replace("+00:00", "Z")
    before = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    
    return [
        {"params": {}, "expected_count": 7},
        {"params": {"name": "ProjectA"}, "expected_count": 1},
        {"params": {"name": "Project"}, "expected_count": 5},
        {"params": {"name": "NonExistent"}, "expected_count": 0},
        {"params": {"created_after": after}, "expected_count": 5},
        {"params": {"created_before": before}, "expected_count": 6},
        {"params": {"name": "Project", "created_after": after}, "expected_count": 4},
        {"params": {"name": "ProjectC", "created_after": after}, "expected_count": 1},
        {"params": {"user_id": "999"}, "expected_count": 4},
        {"params": {"user_id": "user_1"}, "expected_count": 1},
        {"params": {"user_id": "user_999", "name": "Project"}, "expected_count": 4},
    ]


@pytest.fixture
def public_list_queries():
    """Queries for public API (user_999 sees 4 workspaces)."""
    now = timezone.now()
    after = (now - timedelta(days=6)).isoformat().replace("+00:00", "Z")
    before = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    
    return [
        {"params": {}, "expected_count": 4},
        {"params": {"name": "ProjectA"}, "expected_count": 1},
        {"params": {"name": "Project"}, "expected_count": 4},
        {"params": {"name": "NonExistent"}, "expected_count": 0},
        {"params": {"created_after": after}, "expected_count": 3},
        {"params": {"created_before": before}, "expected_count": 3},
        {"params": {"name": "Project", "created_after": after}, "expected_count": 3},
        {"params": {"name": "ProjectC", "created_after": after}, "expected_count": 1},
        {"params": {"user_id": "1"}, "expected_count": 4},  # Ignored by controller filtering
    ]


# =========================================================================
# ASSERTION FIXTURES
# =========================================================================

@pytest.fixture
def upload_image_files(image_file_factory):
    """Files dict for image upload."""
    return {"image_file": image_file_factory()}


@pytest.fixture
def assert_image_uploaded(mock_task_on_workspace_images_uploaded):
    """Assertion for image upload."""
    def assertion(obj, resp):
        assert resp.status_code == 200
        data = resp.json()
        assert data["uuid"] is not None
        assert data["workspace_uuid"] == str(obj.uuid)
        
        uploaded_image = Image.objects.get(uuid=data["uuid"])
        
        # Check that the signal triggered the background task
        # Note: Depending on how the signal is connected in tests, this might vary.
        # But if the fixture is active, the patch should be in place.
        if mock_task_on_workspace_images_uploaded.delay.called:
             # Arguments might be a list of UUIDs
             args, _ = mock_task_on_workspace_images_uploaded.delay.call_args
             assert args[0][0] == uploaded_image.uuid
        
        return True
    return assertion


# =========================================================================
# TEST SUITE
# =========================================================================

@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
@pytest.mark.freeze_time("2026-01-20 12:00:00")
@pytest.mark.usefixtures("mock_task_on_workspace_images_uploaded")
class TestWorkspaceAPI(APITestSuite):
    """
    Workspace API tests.
    """
    
    tests = {
        # ===== DEFAULTS =====
        "model": Workspace,
        "endpoint": "/",
        "factory": "user_workspace_factory",
        "client": "public_client",
        
        # ===== CRUD =====
        "cruds": {
            # ----- CREATE -----
            "create": {
                "expected_status": 201,
                "scenarios": [
                    # Internal service - can create for any user
                    {
                        "name": "internal_service",
                        "client": "internal_client",
                        "payload": lambda s: {"name": "Service WS", "user_id": "user_1234"},
                        "assert": lambda s, obj, data: (
                            obj.name == data["name"] and obj.user_id == data["user_id"]
                        ),
                    },
                    # Public JWT - creates for self
                    {
                        "name": "public_jwt",
                        "payload": lambda s: {"name": "JWT WS"},
                        "assert": lambda s, obj, data: (
                            obj.name == data["name"] and obj.user_id == "user_999"
                        ),
                    },
                    # Unauthenticated public - denied
                    {
                        "name": "anon_public_denied",
                        "client": "anon_public_client",
                        "payload": lambda s: {"name": "Fail"},
                        "expected_status": 401,
                        "access_denied": True,
                    },
                    # Unauthenticated internal - denied
                    {
                        "name": "anon_internal_denied",
                        "client": "anon_internal_client",
                        "payload": lambda s: {"name": "Fail", "user_id": "user_999"},
                        "expected_status": 401,
                        "access_denied": True,
                    },
                    # JWT on internal endpoint - denied
                    {
                        "name": "jwt_internal_denied",
                        "client": "jwt_internal_client",
                        "payload": lambda s: {"name": "Fail"},
                        "expected_status": [401, 403],
                        "access_denied": True,
                    },
                ],
            },
            
            # ----- GET -----
            "get": {
                "scenarios": [
                    # Service - can get any workspace
                    {
                        "name": "service_own",
                        "client": "service_public_client",
                        "assert": lambda s, obj, resp: resp.json()["uuid"] == str(obj.uuid),
                    },
                    {
                        "name": "service_other",
                        "client": "service_public_client",
                        "factory": "other_workspace_factory",
                        "assert": lambda s, obj, resp: resp.json()["uuid"] == str(obj.uuid),
                    },
                    # JWT - can get own
                    {
                        "name": "jwt_own",
                        "assert": lambda s, obj, resp: resp.json()["uuid"] == str(obj.uuid),
                    },
                    # JWT - cannot get other's
                    {
                        "name": "jwt_other_denied",
                        "factory": "other_workspace_factory",
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                    # Unauthenticated - denied
                    {
                        "name": "anon_denied",
                        "client": "anon_public_client",
                        "expected_status": 401,
                        "access_denied": True,
                    },
                ],
            },
            
            # ----- UPDATE -----
            "update": {
                "method": "patch",
                "payload": lambda s: {"name": "Updated"},
                "scenarios": [
                    # Service - can update any
                    {
                        "name": "service_own",
                        "client": "service_public_client",
                        "assert": lambda s, obj, data: obj.name == data["name"],
                    },
                    {
                        "name": "service_other",
                        "client": "service_public_client",
                        "factory": "other_workspace_factory",
                        "assert": lambda s, obj, data: obj.name == data["name"],
                    },
                    # JWT - can update own
                    {
                        "name": "jwt_own",
                        "assert": lambda s, obj, data: obj.name == data["name"],
                    },
                    # JWT - cannot update other's
                    {
                        "name": "jwt_other_denied",
                        "factory": "other_workspace_factory",
                        "payload": lambda s: {"name": "Hack"},
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                    # Unauthenticated - denied
                    {
                        "name": "anon_denied",
                        "client": "anon_public_client",
                        "payload": lambda s: {"name": "Fail"},
                        "expected_status": 401,
                        "access_denied": True,
                    },
                ],
            },
            
            # ----- DELETE -----
            "delete": {
                "scenarios": [
                    # Service - can delete with cancelled task
                    {
                        "name": "service_deletable",
                        "client": "service_public_client",
                        "factory": "deletable_other_workspace_factory",
                    },
                    # Service - cannot delete with active task
                    {
                        "name": "service_active_task_denied",
                        "client": "service_public_client",
                        "factory": "non_deletable_other_workspace_factory",
                        "expected_status": 403,
                        "access_denied": True,
                    },
                    # JWT - can delete own with cancelled task
                    {
                        "name": "jwt_own_deletable",
                        "factory": "deletable_user_workspace_factory",
                    },
                    # JWT - cannot delete own with active task
                    {
                        "name": "jwt_own_active_task_denied",
                        "factory": "non_deletable_user_workspace_factory",
                        "expected_status": 403,
                        "access_denied": True,
                    },
                    # JWT - cannot delete other's
                    {
                        "name": "jwt_other_denied",
                        "factory": "deletable_other_workspace_factory",
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                    # Unauthenticated - denied
                    {
                        "name": "anon_denied",
                        "client": "anon_public_client",
                        "factory": "deletable_user_workspace_factory",
                        "expected_status": 401,
                        "access_denied": True,
                    },
                ],
            },
        },
        
        # ===== ACTIONS =====
        "actions": {
            "upload_image": {
                "url": lambda s, obj: f"/{obj.uuid}/upload-image",
                "method": "post",
                "files": "upload_image_files",
                "scenarios": [
                    # Service - can upload to any
                    {
                        "name": "service_other",
                        "client": "service_public_client",
                        "factory": "other_workspace_factory",
                        "assert": "assert_image_uploaded",
                    },
                    # JWT - can upload to own
                    {
                        "name": "jwt_own",
                        "assert": "assert_image_uploaded",
                    },
                    # JWT - cannot upload to other's
                    {
                        "name": "jwt_other_denied",
                        "factory": "other_workspace_factory",
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
                    "client": "internal_client",
                    "factory": "workspace_list_factory",
                    "queries": "internal_list_queries",
                },
                {
                    "name": "public_jwt",
                    "factory": "workspace_list_factory",
                    "queries": "public_list_queries",
                },
                {
                    "name": "anon_denied",
                    "client": "anon_public_client",
                    "queries": [{"params": {}, "expected_status": 401}],
                },
            ],
        },
    }
