import pytest
from uuid import uuid4
from datetime import timedelta
from django.utils import timezone
from ninja_extra.testing import TestClient

from app.api.models.gcp import GroundControlPoint
from app.api.models.workspace import Workspace
from app.api.controllers.gcp import GCPControllerInternal, GCPControllerPublic
from tests.utils import APITestSuite, AuthStrategyEnum, AuthenticatedTestClient


# =========================================================================
# FIXTURES
# =========================================================================

# -------------------------
# Clients
# -------------------------

@pytest.fixture
def gcp_public_client():
    """JWT authenticated client for public GCP API."""
    return AuthenticatedTestClient(
        GCPControllerPublic, auth=AuthStrategyEnum.jwt
    )


@pytest.fixture
def gcp_internal_client():
    """Service authenticated client for internal GCP API."""
    return AuthenticatedTestClient(
        GCPControllerInternal, auth=AuthStrategyEnum.service
    )


@pytest.fixture
def gcp_anon_public_client():
    """Unauthenticated client for public GCP API."""
    return TestClient(GCPControllerPublic)


@pytest.fixture
def gcp_anon_internal_client():
    """Unauthenticated client for internal GCP API."""
    return TestClient(GCPControllerInternal)


@pytest.fixture
def gcp_jwt_internal_client():
    """JWT client for internal GCP API (should be denied)."""
    return AuthenticatedTestClient(
        GCPControllerInternal, auth=AuthStrategyEnum.jwt
    )


# -------------------------
# Workspace/Image Fixtures
# -------------------------

@pytest.fixture
def user_gcp_workspace(workspace_factory):
    """Workspace owned by user_999 for GCP tests."""
    return workspace_factory(user_id="user_999")


@pytest.fixture
def other_gcp_workspace(workspace_factory):
    """Workspace owned by another user for GCP tests."""
    return workspace_factory(user_id="user_other")


@pytest.fixture
def user_gcp_image(image_factory, user_gcp_workspace):
    """Image in user_999's workspace."""
    return image_factory(workspace=user_gcp_workspace)


@pytest.fixture
def other_gcp_image(image_factory, other_gcp_workspace):
    """Image in other user's workspace."""
    return image_factory(workspace=other_gcp_workspace)


# -------------------------
# GCP Factories
# -------------------------

@pytest.fixture
def user_gcp_factory(ground_control_point_factory, user_gcp_image):
    """Factory for GCPs in user_999's workspace."""
    def factory(**kwargs):
        return ground_control_point_factory(image=user_gcp_image, **kwargs)
    return factory


@pytest.fixture
def other_gcp_factory(ground_control_point_factory, other_gcp_image):
    """Factory for GCPs in other user's workspace."""
    def factory(**kwargs):
        return ground_control_point_factory(image=other_gcp_image, **kwargs)
    return factory


@pytest.fixture
def any_gcp_factory(ground_control_point_factory, image_factory, workspace_factory):
    """Factory for GCPs in any workspace."""
    def factory(**kwargs):
        ws = workspace_factory()
        img = image_factory(workspace=ws)
        return ground_control_point_factory(image=img, **kwargs)
    return factory


# -------------------------
# GCP List Factory
# -------------------------

@pytest.fixture
def gcp_list_factory(workspace_factory, image_factory, ground_control_point_factory):
    """Factory for GCP list (filtering tests)."""
    def factory():
        GroundControlPoint.objects.all().delete()
        Workspace.objects.all().delete()
        
        now = timezone.now()
        user_ws = workspace_factory(user_id="user_999")
        other_ws1 = workspace_factory(user_id="user_1")
        other_ws2 = workspace_factory(user_id="user_2")

        def create_gcp(workspace, label, days_ago):
            img = image_factory(workspace=workspace)
            return ground_control_point_factory(
                image=img,
                label=label,
                created_at=now - timedelta(days=days_ago),
            )

        gcps = [
            create_gcp(user_ws, "GCP_A", 0),
            create_gcp(user_ws, "GCP_B", 1),
            create_gcp(user_ws, "GCP_C", 3),
            create_gcp(user_ws, "GCP_D", 5),
            create_gcp(user_ws, "GCP_E", 7),
            create_gcp(other_ws1, "GCP_F", 2),
            create_gcp(other_ws1, "GCP_G", 4),
            create_gcp(other_ws2, "GCP_H", 6),
            create_gcp(other_ws2, "GCP_I", 8),
            create_gcp(other_ws2, "GCP_J", 10),
        ]

        return {
            "user_ws": user_ws,
            "other_ws1": other_ws1,
            "other_ws2": other_ws2,
            "gcps": gcps,
            "user_image": gcps[0].image,
        }
    yield factory
    GroundControlPoint.objects.all().delete()


# -------------------------
# List Queries
# -------------------------

@pytest.fixture
def internal_gcp_list_queries(gcp_list_factory):
    """Queries for internal GCP API (sees all 10 GCPs)."""
    data = gcp_list_factory()
    now = timezone.now()
    after = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
    before = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    ws1_uuid = str(data["user_ws"].uuid)
    ws2_uuid = str(data["other_ws1"].uuid)
    ws3_uuid = str(data["other_ws2"].uuid)
    image_a_uuid = str(data["gcps"][0].image.uuid)
    
    return [
        {"params": {}, "expected_count": 10},
        {"params": {"label": "GCP_A"}, "expected_count": 1},
        {"params": {"label": "GCP"}, "expected_count": 10},
        {"params": {"created_after": after, "created_before": before}, "expected_count": 4},
        {"params": {"created_after": after}, "expected_count": 6},
        {"params": {"created_before": before}, "expected_count": 8},
        {"params": {"workspace_uuid": ws1_uuid}, "expected_count": 5},
        {"params": {"workspace_uuid": ws2_uuid}, "expected_count": 2},
        {"params": {"workspace_uuid": ws3_uuid}, "expected_count": 3},
        {"params": {"image_uuid": image_a_uuid}, "expected_count": 1},
        {"params": {"workspace_uuid": ws1_uuid, "label": "GCP_A"}, "expected_count": 1},
    ]


@pytest.fixture
def public_gcp_list_queries(gcp_list_factory):
    """Queries for public GCP API (user_999 sees only 5 GCPs)."""
    data = gcp_list_factory()
    now = timezone.now()
    after = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
    before = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    ws_own_uuid = str(data["user_ws"].uuid)
    ws_other_uuid = str(data["other_ws1"].uuid)
    image_own_uuid = str(data["gcps"][0].image.uuid)
    
    return [
        {"params": {}, "expected_count": 5},
        {"params": {"label": "GCP_C"}, "expected_count": 1},
        {"params": {"label": "GCP"}, "expected_count": 5},
        {"params": {"label": "GCP_INVALID"}, "expected_count": 0},
        {"params": {"created_after": after}, "expected_count": 4},
        {"params": {"created_before": before}, "expected_count": 3},
        {"params": {"created_after": after, "created_before": before}, "expected_count": 2},
        {"params": {"workspace_uuid": ws_own_uuid}, "expected_count": 5},
        {"params": {"workspace_uuid": ws_other_uuid}, "expected_count": 0},
        {"params": {"image_uuid": image_own_uuid}, "expected_count": 1},
    ]


# -------------------------
# Create Fixtures
# -------------------------

@pytest.fixture
def user_image_for_create(image_factory, user_gcp_workspace):
    """Image for create tests."""
    return image_factory(workspace=user_gcp_workspace)


@pytest.fixture
def other_image_for_create(image_factory, other_gcp_workspace):
    """Other user's image for create tests."""
    return image_factory(workspace=other_gcp_workspace)


@pytest.fixture
def any_image_for_create(image_factory, workspace_factory):
    """Any image for create tests."""
    ws = workspace_factory()
    return image_factory(workspace=ws)


@pytest.fixture
def payload_create_service(any_image_for_create):
    """Valid payload for service account (any image)."""
    return {
        "image_uuid": str(any_image_for_create.uuid),
        "gcp_point": [12.34, 56.78, 100.0],
        "image_point": [500.0, 300.0],
        "label": "GCP-SERVICE-001",
    }

@pytest.fixture
def payload_create_own(user_image_for_create):
    """Valid payload for user (own image)."""
    return {
        "image_uuid": str(user_image_for_create.uuid),
        "gcp_point": [12.34, 56.78, 100.0],
        "image_point": [500.0, 300.0],
        "label": "GCP-USER-001",
    }


@pytest.fixture
def payload_create_other(other_image_for_create):
    """Payload trying to create GCP on someone else's image."""
    return {
        "image_uuid": str(other_image_for_create.uuid),
        "gcp_point": [12.34, 56.78, 100.0],
        "image_point": [500.0, 300.0],
        "label": "GCP-FORBIDDEN",
    }


@pytest.fixture
def payload_create_invalid_point(any_image_for_create):
    """Invalid payload (bad geometry)."""
    return {
        "image_uuid": str(any_image_for_create.uuid),
        "gcp_point": [12.34, 56.78],  # Missing Z
        "image_point": [500.0, 300.0],
        "label": "Invalid-GCP",
    }


@pytest.fixture
def payload_create_orphan():
    """Payload with non-existent image UUID."""
    return {
        "image_uuid": str(uuid4()),
        "gcp_point": [10.0, 10.0, 10.0],
        "image_point": [10.0, 10.0],
        "label": "Orphan",
    }


@pytest.fixture
def payload_update_label():
    return {"label": "updated-label"}


@pytest.fixture
def payload_update_coords():
    return {
        "gcp_point": [98.76, 54.32, 200.0],
        "image_point": [100.0, 150.0],
    }


# -------------------------
# Assertions
# -------------------------

@pytest.fixture
def assert_gcp_created():
    """Assertion for successful GCP creation."""
    def assertion(obj, payload):
        assert obj.label == payload["label"]
        assert list(obj.point) == payload["gcp_point"]
        assert [obj.imgx, obj.imgy] == payload["image_point"]
        return True
    return assertion


@pytest.fixture
def assert_gcp_updated():
    """Assertion for successful GCP update."""
    def assertion(obj, payload):
        for key, value in payload.items():
            if key == "gcp_point":
                assert list(obj.point) == value
            elif key == "image_point":
                 assert [obj.imgx, obj.imgy] == value
            else:
                assert getattr(obj, key) == value
        return True
    return assertion


@pytest.fixture
def assert_gcp_deleted():
    """Assertion for successful GCP deletion."""
    def assertion(obj, resp):
        assert resp.status_code == 204
        assert not GroundControlPoint.objects.filter(pk=obj.pk).exists()
        return True
    return assertion


@pytest.fixture
def assert_geojson_response():
    """Assertion for GeoJSON response."""
    def assertion(obj, resp):
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "FeatureCollection"
        assert "features" in data
        return True
    return assertion


# =========================================================================
# TEST SUITE
# =========================================================================

@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
@pytest.mark.freeze_time("2026-01-20 12:00:00")
class TestGCPAPI(APITestSuite):
    """
    GCP API tests.
    
    Covers:
    - Internal API (service auth)
    - Public API (JWT auth)
    - Unauthorized access
    - CRUD operations
    - List filtering
    - GeoJSON export
    """
    
    tests = {
        # ===== DEFAULTS =====
        "model": GroundControlPoint,
        "endpoint": "/",
        "factory": "user_gcp_factory",
        "client": "gcp_public_client",
        
        # ===== CRUD =====
        "cruds": {
            # ----- CREATE -----
            "create": {
                "expected_status": 201,
                "assertion": "assert_gcp_created",
                "scenarios": [
                    {
                        "name": "jwt_own_image",
                        "payload": lambda s: s.fixture("payload_create_own"),
                        "expected_status": 201,
                    },
                    {
                        "name": "jwt_other_image_denied",
                        "payload": lambda s: s.fixture("payload_create_other"),
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                    {
                        "name": "anon_public_denied",
                        "client": "gcp_anon_public_client",
                        "payload": lambda s: s.fixture("payload_create_own"),
                        "expected_status": 401,
                        "access_denied": True,
                    },
                    {
                        "name": "nonexistent_image_denied",
                        "payload": lambda s: s.fixture("payload_create_orphan"),
                        "expected_status": 404,
                        "access_denied": True,
                    },
                    {
                        "name": "invalid_gcp_point",
                        "payload": lambda s: s.fixture("payload_create_invalid_point"),
                        "expected_status": 422,
                        "access_denied": True,
                    },
                ],
            },
            
            # ----- GET -----
            "get": {
                "scenarios": [
                    {
                        "name": "jwt_own",
                    },
                    {
                        "name": "jwt_other_denied",
                        "factory": "other_gcp_factory",
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                    {
                        "name": "anon_denied",
                        "client": "gcp_anon_public_client",
                        "expected_status": 401,
                        "access_denied": True,
                    },
                ],
            },
            
            # ----- UPDATE -----
            "update": {
                "method": "patch", # Controller specifies PATCH route
                "assertion": "assert_gcp_updated",
                "scenarios": [
                    {
                        "name": "jwt_own",
                        "payload": lambda s: s.fixture("payload_update_label"),
                    },
                    {
                        "name": "jwt_other_denied",
                        "factory": "other_gcp_factory",
                        "payload": lambda s: s.fixture("payload_update_label"),
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                ],
            },
            
            # ----- DELETE -----
            "delete": {
                "assertion": "assert_gcp_deleted",
                "scenarios": [
                    {
                        "name": "jwt_own",
                    },
                    {
                        "name": "jwt_other_denied",
                        "factory": "other_gcp_factory",
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                ],
            },
        },
        
        # ===== ACTIONS =====
        "actions": {
            "geojson": {
                "url": "/geojson",
                "method": "get",
                "assertion": "assert_geojson_response",
                "scenarios": [
                    {
                        "name": "jwt_own",
                        "factory": "user_gcp_factory",
                    },
                    {
                        "name": "anon_denied",
                        "client": "gcp_anon_public_client",
                        "expected_status": 401,
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
                    "client": "gcp_internal_client",
                    "queries": "internal_gcp_list_queries",
                },
                {
                    "name": "public_jwt",
                    "queries": "public_gcp_list_queries",
                },
                {
                    "name": "anon_public_denied",
                    "client": "gcp_anon_public_client",
                    "queries": [{"params": {}, "expected_status": 401}],
                },
            ],
        },
    }
