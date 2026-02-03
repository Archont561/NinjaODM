import pytest
from datetime import timedelta
from django.utils import timezone
from ninja_extra.testing import TestClient

from app.api.models.image import Image
from app.api.controllers.image import ImageControllerInternal, ImageControllerPublic
from tests.utils import AuthStrategyEnum, AuthenticatedTestClient, APITestSuite


# =========================================================================
# FIXTURES
# =========================================================================

# -------------------------
# Clients
# -------------------------


@pytest.fixture
def image_public_client():
    """JWT authenticated client for public Image API."""
    return AuthenticatedTestClient(ImageControllerPublic, auth=AuthStrategyEnum.jwt)


@pytest.fixture
def image_internal_client():
    """Service authenticated client for internal Image API."""
    return AuthenticatedTestClient(
        ImageControllerInternal, auth=AuthStrategyEnum.service
    )


@pytest.fixture
def image_anon_public_client():
    """Unauthenticated client for public Image API."""
    return TestClient(ImageControllerPublic)


@pytest.fixture
def image_anon_internal_client():
    """Unauthenticated client for internal Image API."""
    return TestClient(ImageControllerInternal)


@pytest.fixture
def image_jwt_internal_client():
    """JWT client for internal Image API (should be denied)."""
    return AuthenticatedTestClient(ImageControllerInternal, auth=AuthStrategyEnum.jwt)


# -------------------------
# Workspace Fixtures
# -------------------------


@pytest.fixture
def user_image_workspace(workspace_factory):
    """Workspace owned by user_999 for image tests."""
    return workspace_factory(user_id="user_999")


@pytest.fixture
def other_image_workspace(workspace_factory):
    """Workspace owned by another user for image tests."""
    return workspace_factory(user_id="user_other")


# -------------------------
# Image Factories
# -------------------------]


@pytest.fixture
def user_image_factory(image_factory, user_image_workspace, image_file_factory):
    """Factory for images with file in user_999's workspace."""

    def factory(**kwargs):
        file_obj = image_file_factory()
        data = {"workspace": user_image_workspace, "image_file": file_obj, **kwargs}
        return image_factory(**data)

    return factory


@pytest.fixture
def other_image_factory(user_image_factory, other_image_workspace):
    """Factory for images with file in other user's workspace."""

    def factory(**kwargs):
        return user_image_factory(workspace=other_image_workspace)

    return factory


# -------------------------
# Image List Factory
# -------------------------


@pytest.fixture
def image_list_factory(workspace_factory, image_factory):
    """Factory for image list (filtering tests)."""

    def factory():
        # Clear existing data
        Image.objects.all().delete()

        now = timezone.now()
        user_ws = workspace_factory(user_id="user_999")
        other_ws1 = workspace_factory(user_id="user_1")
        other_ws2 = workspace_factory(user_id="user_2")

        def create_image(workspace, name, is_thumbnail, days_ago):
            return image_factory(
                workspace=workspace,
                name=name,
                is_thumbnail=is_thumbnail,
                created_at=now - timedelta(days=days_ago),
            )

        return {
            "user_ws": user_ws,
            "other_ws1": other_ws1,
            "other_ws2": other_ws2,
            "images": [
                create_image(user_ws, "Image_1", True, 1),
                create_image(user_ws, "Image_2", False, 2),
                create_image(other_ws1, "Image_3", True, 5),
                create_image(other_ws1, "Image_4", False, 10),
                create_image(other_ws2, "Image_5", True, 3),
                create_image(other_ws2, "Image_6", False, 7),
            ],
        }

    yield factory
    Image.objects.all().delete()


# -------------------------
# List Queries
# -------------------------


@pytest.fixture
def internal_image_list_queries(image_list_factory):
    """Queries for internal Image API (sees all 6 images)."""
    data = image_list_factory()
    now = timezone.now()
    after = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
    ws1_uuid = str(data["other_ws1"].uuid)

    return [
        {"params": {}, "expected_count": 6},
        {"params": {"name": "Image_1"}, "expected_count": 1},
        {"params": {"is_thumbnail": True}, "expected_count": 3},
        {"params": {"created_after": after}, "expected_count": 4},
        {"params": {"workspace_uuid": ws1_uuid}, "expected_count": 2},
    ]


@pytest.fixture
def public_image_list_queries(image_list_factory):
    """Queries for public Image API (user_999 sees only 2 images)."""
    data = image_list_factory()
    now = timezone.now()
    after = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
    ws_own_uuid = str(data["user_ws"].uuid)
    ws_other_uuid = str(data["other_ws1"].uuid)

    return [
        {"params": {}, "expected_count": 2},
        {"params": {"name": "Image_1"}, "expected_count": 1},
        {"params": {"is_thumbnail": "True"}, "expected_count": 1},
        {"params": {"created_after": after}, "expected_count": 2},
        {"params": {"workspace_uuid": ws_own_uuid}, "expected_count": 2},
        {"params": {"workspace_uuid": ws_other_uuid}, "expected_count": 0},
    ]


# -------------------------
# Assertions
# -------------------------


@pytest.fixture
def assert_image_deleted():
    """Assertion that image and file are deleted."""

    def assertion(obj, resp):
        assert resp.status_code == 204
        assert not Image.objects.filter(pk=obj.pk).exists()
        return True

    return assertion


@pytest.fixture
def assert_image_download(image_file_factory):
    """Assertion for image download."""

    def assertion(obj, resp):
        assert resp.status_code == 200
        assert "image/jpeg" in resp.headers.get("Content-Type", "")
        assert "attachment" in resp.headers.get("Content-Disposition", "")

        simple_image = image_file_factory()
        assert resp.content == simple_image.read()
        return True

    return assertion


# =========================================================================
# TEST SUITE
# =========================================================================


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
@pytest.mark.freeze_time("2026-01-20 12:00:00")
class TestImageAPI(APITestSuite):
    """
    Image API tests.
    """

    tests = {
        # ===== DEFAULTS =====
        "model": Image,
        "endpoint": "/",
        "factory": "user_image_factory",
        "client": "image_public_client",
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
                        "factory": "other_image_factory",
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                    {
                        "name": "anon_public_denied",
                        "client": "image_anon_public_client",
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
                        "assert": "assert_image_deleted",
                    },
                    {
                        "name": "jwt_other_denied",
                        "factory": "other_image_factory",
                        "expected_status": [403, 404],
                        "access_denied": True,
                    },
                ],
            },
        },
        # ===== ACTIONS =====
        "actions": {
            "download": {
                "url": lambda s, obj: f"/{obj.uuid}/download",
                "method": "get",
                "scenarios": [
                    {
                        "name": "jwt_own",
                        "assert": "assert_image_download",
                    },
                    {
                        "name": "jwt_other_denied",
                        "factory": "other_image_factory",
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
                    "client": "image_internal_client",
                    "queries": "internal_image_list_queries",
                },
                {
                    "name": "public_jwt",
                    "queries": "public_image_list_queries",
                },
                {
                    "name": "anon_denied",
                    "client": "image_anon_public_client",
                    "queries": [{"params": {}, "expected_status": 401}],
                },
                {
                    "name": "jwt_internal_denied",
                    "client": "image_jwt_internal_client",
                    "queries": [{"params": {}, "expected_status": [401, 403]}],
                },
            ],
        },
    }
