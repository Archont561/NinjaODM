import pytest
from uuid import uuid4
from ninja_extra.testing import TestClient

from app.api.models.gcp import GroundControlPoint
from app.api.controllers.gcp import GCPControllerInternal, GCPControllerPublic
from ..auth_clients import AuthStrategyEnum, AuthenticatedTestClient


@pytest.mark.django_db
class TestGCPAPIInternal:
    @classmethod
    def setup_method(cls):
        cls.client = AuthenticatedTestClient(
            GCPControllerInternal, auth=AuthStrategyEnum.service
        )

    def test_list_all_gcps(self, ground_control_point_factory):
        ground_control_point_factory.create_batch(5)
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_retrieve_any_gcp(self, ground_control_point_factory):
        gcp = ground_control_point_factory()
        response = self.client.get(f"/{gcp.uuid}")
        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == str(gcp.uuid)
        assert data["label"] == gcp.label

    def test_create_gcp(self, image_factory):
        image = image_factory()
        payload = {
            "gcp_point": [12.34, 56.78, 100.0],
            "image_point": [500.0, 300.0],
            "label": "GCP-001",
        }
        response = self.client.post(
            f"/?image_uuid={image.uuid}",
            json=payload,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["label"] == "GCP-001"
        assert data["image_uuid"] == str(image.uuid)
        assert data["gcp_point"] == [12.34, 56.78, 100.0]
        assert data["image_point"] == [500.0, 300.0]

    def test_update_gcp(self, ground_control_point_factory):
        gcp = ground_control_point_factory(label="old-label")
        payload = {"label": "new-label"}
        response = self.client.patch(
            f"/{gcp.uuid}",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "new-label"

    def test_update_gcp_coordinates(self, ground_control_point_factory):
        gcp = ground_control_point_factory()
        payload = {
            "gcp_point": [98.76, 54.32, 200.0],
            "image_point": [100.0, 150.0],
        }
        response = self.client.patch(
            f"/{gcp.uuid}",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["gcp_point"] == [98.76, 54.32, 200.0]
        assert data["image_point"] == [100.0, 150.0]

    def test_delete_any_gcp(self, ground_control_point_factory):
        gcp = ground_control_point_factory()
        response = self.client.delete(f"/{gcp.uuid}")
        assert response.status_code == 204
        assert not GroundControlPoint.objects.filter(pk=gcp.pk).exists()

    def test_retrieve_nonexistent_gcp_returns_404(self):
        fake_uuid = uuid4()
        response = self.client.get(f"/{fake_uuid}")
        assert response.status_code == 404

    def test_create_gcp_invalid_gcp_point(self, image_factory):
        image = image_factory()
        payload = {
            "gcp_point": [12.34, 56.78],  # Missing altitude
            "image_point": [500.0, 300.0],
            "label": "Invalid-GCP",
        }
        response = self.client.post(
            f"/?image_uuid={image.uuid}",
            json=payload,
        )
        assert response.status_code == 422

    def test_create_gcp_invalid_image_point(self, image_factory):
        image = image_factory()
        payload = {
            "gcp_point": [12.34, 56.78, 100.0],
            "image_point": [500.0],  # Missing y coordinate
            "label": "Invalid-GCP",
        }
        response = self.client.post(
            f"/?image_uuid={image.uuid}",
            json=payload,
        )
        assert response.status_code == 422

    def test_create_gcp_missing_required_field(self, image_factory):
        image = image_factory()
        payload = {
            "gcp_point": [12.34, 56.78, 100.0],
            "image_point": [500.0, 300.0],
            # Missing label
        }
        response = self.client.post(
            f"/?image_uuid={image.uuid}",
            json=payload,
        )
        assert response.status_code == 422

    def test_create_gcp_missing_image_uuid(self):
        payload = {
            "gcp_point": [12.34, 56.78, 100.0],
            "image_point": [500.0, 300.0],
            "label": "No-Image",
        }
        response = self.client.post("/", json=payload)
        assert response.status_code in (403, 404)

    def test_create_gcp_nonexistent_image(self):
        fake_image_uuid = uuid4()
        payload = {
            "gcp_point": [12.34, 56.78, 100.0],
            "image_point": [500.0, 300.0],
            "label": "Orphan-GCP",
        }
        response = self.client.post(
            f"/?image_uuid={fake_image_uuid}",
            json=payload,
        )
        assert response.status_code in (403, 404)


@pytest.mark.django_db
class TestGCPAPIPublic:
    @classmethod
    def setup_method(cls):
        cls.client = AuthenticatedTestClient(
            GCPControllerPublic, auth=AuthStrategyEnum.jwt
        )

    def test_list_user_gcps_only(
        self, workspace_factory, image_factory, ground_control_point_factory
    ):
        user_workspace = workspace_factory(user_id=999)
        other_workspace = workspace_factory(user_id=123)

        user_image = image_factory(workspace=user_workspace)
        other_image = image_factory(workspace=other_workspace)

        user_gcp = ground_control_point_factory(image=user_image)
        ground_control_point_factory(image=other_image)  # Should NOT be visible

        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["uuid"] == str(user_gcp.uuid)

    def test_list_as_geojson(
        self, workspace_factory, image_factory, ground_control_point_factory
    ):
        user_workspace = workspace_factory(user_id=999)
        user_image = image_factory(workspace=user_workspace)
        ground_control_point_factory(image=user_image, label="GeoJSON-Test")

        response = self.client.get("/geojson")
        assert response.status_code == 200
        data = response.json()

        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1

        feature = data["features"][0]
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "Point"
        assert feature["properties"]["label"] == "GeoJSON-Test"
        assert feature["properties"]["image_uuid"] == str(user_image.uuid)

    def test_retrieve_own_gcp(
        self, workspace_factory, image_factory, ground_control_point_factory
    ):
        user_workspace = workspace_factory(user_id=999)
        user_image = image_factory(workspace=user_workspace)
        gcp = ground_control_point_factory(image=user_image)

        response = self.client.get(f"/{gcp.uuid}")
        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == str(gcp.uuid)
        assert data["image_uuid"] == str(user_image.uuid)
        assert "created_at" in data

    def test_cannot_access_others_gcp(
        self, workspace_factory, image_factory, ground_control_point_factory
    ):
        other_workspace = workspace_factory(user_id=456)
        other_image = image_factory(workspace=other_workspace)
        other_gcp = ground_control_point_factory(image=other_image)

        response = self.client.get(f"/{other_gcp.uuid}")
        assert response.status_code in (403, 404)

    def test_create_gcp_for_own_image(self, workspace_factory, image_factory):
        user_workspace = workspace_factory(user_id=999)
        user_image = image_factory(workspace=user_workspace)

        payload = {
            "gcp_point": [12.34, 56.78, 100.0],
            "image_point": [500.0, 300.0],
            "label": "GCP-USER-001",
        }
        response = self.client.post(f"/?image_uuid={user_image.uuid}", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["label"] == "GCP-USER-001"
        assert data["image_uuid"] == str(user_image.uuid)

    def test_cannot_create_gcp_for_others_image(self, workspace_factory, image_factory):
        other_workspace = workspace_factory(user_id=456)
        other_image = image_factory(workspace=other_workspace)

        payload = {
            "gcp_point": [12.34, 56.78, 100.0],
            "image_point": [500.0, 300.0],
            "label": "GCP-FORBIDDEN",
        }
        response = self.client.post(f"/?image_uuid={other_image.uuid}", json=payload)
        assert response.status_code in (403, 404)

    def test_update_own_gcp(
        self, workspace_factory, image_factory, ground_control_point_factory
    ):
        user_workspace = workspace_factory(user_id=999)
        user_image = image_factory(workspace=user_workspace)
        gcp = ground_control_point_factory(image=user_image, label="old-label")

        payload = {"label": "updated-label"}
        response = self.client.patch(f"/{gcp.uuid}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "updated-label"

    def test_cannot_update_others_gcp(
        self, workspace_factory, image_factory, ground_control_point_factory
    ):
        other_workspace = workspace_factory(user_id=456)
        other_image = image_factory(workspace=other_workspace)
        other_gcp = ground_control_point_factory(image=other_image)

        payload = {"label": "hacked"}
        response = self.client.patch(f"/{other_gcp.uuid}", json=payload)
        assert response.status_code in (403, 404)

    def test_delete_own_gcp(
        self, workspace_factory, image_factory, ground_control_point_factory
    ):
        user_workspace = workspace_factory(user_id=999)
        user_image = image_factory(workspace=user_workspace)
        gcp = ground_control_point_factory(image=user_image)

        response = self.client.delete(f"/{gcp.uuid}")
        assert response.status_code == 204
        assert not GroundControlPoint.objects.filter(pk=gcp.pk).exists()

    def test_cannot_delete_others_gcp(
        self, workspace_factory, image_factory, ground_control_point_factory
    ):
        other_workspace = workspace_factory(user_id=456)
        other_image = image_factory(workspace=other_workspace)
        other_gcp = ground_control_point_factory(image=other_image)

        response = self.client.delete(f"/{other_gcp.uuid}")
        assert response.status_code in (403, 404)
        assert GroundControlPoint.objects.filter(pk=other_gcp.pk).exists()


@pytest.mark.django_db
class TestGCPAPIUnauthorized:
    @classmethod
    def setup_method(cls):
        cls.public_client = TestClient(GCPControllerPublic)
        cls.internal_client = TestClient(GCPControllerInternal)
        cls.user_client = AuthenticatedTestClient(
            GCPControllerInternal, auth=AuthStrategyEnum.jwt
        )

    @pytest.mark.parametrize(
        "method, client_attr, url_template, payload",
        [
            ("get", "public_client", "/", None),
            ("get", "public_client", "/geojson", None),
            ("get", "public_client", "/{uuid}", None),
            (
                "post",
                "public_client",
                "/?image_uuid={image_uuid}",
                {"gcp_point": [0, 0, 0], "image_point": [0, 0], "label": "test"},
            ),
            ("patch", "public_client", "/{uuid}", {"label": "test"}),
            ("delete", "public_client", "/{uuid}", None),
            ("get", "internal_client", "/", None),
            ("get", "internal_client", "/{uuid}", None),
            (
                "post",
                "internal_client",
                "/?image_uuid={image_uuid}",
                {"gcp_point": [0, 0, 0], "image_point": [0, 0], "label": "test"},
            ),
            ("patch", "internal_client", "/{uuid}", {"label": "test"}),
            ("delete", "internal_client", "/{uuid}", None),
            ("get", "user_client", "/", None),
            ("get", "user_client", "/{uuid}", None),
            (
                "post",
                "user_client",
                "/?image_uuid={image_uuid}",
                {"gcp_point": [0, 0, 0], "image_point": [0, 0], "label": "test"},
            ),
            ("patch", "user_client", "/{uuid}", {"label": "test"}),
            ("delete", "user_client", "/{uuid}", None),
        ],
    )
    def test_access_denied(
        self, ground_control_point_factory, method, client_attr, url_template, payload
    ):
        gcp = ground_control_point_factory()
        client = getattr(self, client_attr)
        url = url_template.format(uuid=gcp.uuid, image_uuid=gcp.image.uuid)
        response = getattr(client, method)(url, json=payload)
        assert response.status_code in (401, 403)
