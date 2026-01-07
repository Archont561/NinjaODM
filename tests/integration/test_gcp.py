import pytest
from uuid import uuid4

from app.api.models.gcp import GroundControlPoint


@pytest.mark.django_db
class TestGCPAPIInternal:
    def test_list_all_gcps(
        self,
        service_api_client,
        ground_control_point_factory,
    ):
        ground_control_point_factory.create_batch(5)
        response = service_api_client.get("/internal/gcps/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_retrieve_any_gcp(
        self,
        service_api_client,
        ground_control_point_factory,
    ):
        gcp = ground_control_point_factory()
        response = service_api_client.get(f"/internal/gcps/{gcp.uuid}")
        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == str(gcp.uuid)
        assert data["label"] == gcp.label

    def test_create_gcp(
        self,
        service_api_client,
        image_factory,
    ):
        image = image_factory()
        payload = {
            "gcp_point": [12.34, 56.78, 100.0],
            "image_point": [500.0, 300.0],
            "label": "GCP-001",
        }
        response = service_api_client.post(
            f"/internal/gcps/?image_uuid={image.uuid}",
            json=payload,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["label"] == "GCP-001"
        assert data["image_uuid"] == str(image.uuid)
        assert data["gcp_point"] == [12.34, 56.78, 100.0]
        assert data["image_point"] == [500.0, 300.0]

    def test_update_gcp(
        self,
        service_api_client,
        ground_control_point_factory,
    ):
        gcp = ground_control_point_factory(label="old-label")
        payload = {"label": "new-label"}
        response = service_api_client.patch(
            f"/internal/gcps/{gcp.uuid}",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "new-label"

    def test_update_gcp_coordinates(
        self,
        service_api_client,
        ground_control_point_factory,
    ):
        gcp = ground_control_point_factory()
        payload = {
            "gcp_point": [98.76, 54.32, 200.0],
            "image_point": [100.0, 150.0],
        }
        response = service_api_client.patch(
            f"/internal/gcps/{gcp.uuid}",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["gcp_point"] == [98.76, 54.32, 200.0]
        assert data["image_point"] == [100.0, 150.0]

    def test_delete_any_gcp(
        self,
        service_api_client,
        ground_control_point_factory,
    ):
        gcp = ground_control_point_factory()
        response = service_api_client.delete(f"/internal/gcps/{gcp.uuid}")
        assert response.status_code == 204
        assert not GroundControlPoint.objects.filter(pk=gcp.pk).exists()

    def test_retrieve_nonexistent_gcp_returns_404(
        self,
        service_api_client,
    ):
        fake_uuid = uuid4()
        response = service_api_client.get(f"/internal/gcps/{fake_uuid}")
        assert response.status_code == 404

    def test_create_gcp_invalid_gcp_point(
        self,
        service_api_client,
        image_factory,
    ):
        image = image_factory()
        payload = {
            "gcp_point": [12.34, 56.78],  # Missing altitude
            "image_point": [500.0, 300.0],
            "label": "Invalid-GCP",
        }
        response = service_api_client.post(
            f"/internal/gcps/?image_uuid={image.uuid}",
            json=payload,
        )
        assert response.status_code == 422

    def test_create_gcp_invalid_image_point(
        self,
        service_api_client,
        image_factory,
    ):
        image = image_factory()
        payload = {
            "gcp_point": [12.34, 56.78, 100.0],
            "image_point": [500.0],  # Missing y coordinate
            "label": "Invalid-GCP",
        }
        response = service_api_client.post(
            f"/internal/gcps/?image_uuid={image.uuid}",
            json=payload,
        )
        assert response.status_code == 422

    def test_create_gcp_missing_required_field(
        self,
        service_api_client,
        image_factory,
    ):
        image = image_factory()
        payload = {
            "gcp_point": [12.34, 56.78, 100.0],
            "image_point": [500.0, 300.0],
            # Missing label
        }
        response = service_api_client.post(
            f"/internal/gcps/?image_uuid={image.uuid}",
            json=payload,
        )
        assert response.status_code == 422

    def test_create_gcp_missing_image_uuid(self, service_api_client):
        payload = {
            "gcp_point": [12.34, 56.78, 100.0],
            "image_point": [500.0, 300.0],
            "label": "No-Image",
        }
        response = service_api_client.post("/internal/gcps/", json=payload)
        assert response.status_code in (403, 404)

    def test_create_gcp_nonexistent_image(self, service_api_client):
        fake_image_uuid = uuid4()
        payload = {
            "gcp_point": [12.34, 56.78, 100.0],
            "image_point": [500.0, 300.0],
            "label": "Orphan-GCP",
        }
        response = service_api_client.post(
            f"/internal/gcps/?image_uuid={fake_image_uuid}",
            json=payload,
        )
        assert response.status_code in (403, 404)


@pytest.mark.django_db
class TestGCPAPIPublic:
    def test_list_user_gcps_only(
        self,
        service_user_api_client,
        workspace_factory,
        image_factory,
        ground_control_point_factory,
    ):
        # User's workspace (user_id=999 from fixture)
        user_workspace = workspace_factory(user_id=999)
        other_workspace = workspace_factory(user_id=123)

        user_image = image_factory(workspace=user_workspace)
        other_image = image_factory(workspace=other_workspace)

        user_gcp = ground_control_point_factory(image=user_image)
        ground_control_point_factory(image=other_image)  # Should NOT be visible

        response = service_user_api_client.get("/gcps/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["uuid"] == str(user_gcp.uuid)

    def test_list_as_geojson(
        self,
        service_user_api_client,
        workspace_factory,
        image_factory,
        ground_control_point_factory,
    ):
        user_workspace = workspace_factory(user_id=999)
        user_image = image_factory(workspace=user_workspace)
        gcp = ground_control_point_factory(image=user_image, label="GeoJSON-Test")

        response = service_user_api_client.get("/gcps/geojson")
        assert response.status_code == 200
        data = response.json()

        print(data)

        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1

        feature = data["features"][0]
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "Point"
        assert feature["properties"]["label"] == "GeoJSON-Test"
        assert feature["properties"]["image_uuid"] == str(user_image.uuid)

    def test_list_as_geojson_excludes_others(
        self,
        service_user_api_client,
        workspace_factory,
        image_factory,
        ground_control_point_factory,
    ):
        user_workspace = workspace_factory(user_id=999)
        other_workspace = workspace_factory(user_id=456)

        user_image = image_factory(workspace=user_workspace)
        other_image = image_factory(workspace=other_workspace)

        ground_control_point_factory(image=user_image)
        ground_control_point_factory(image=other_image)

        response = service_user_api_client.get("/gcps/geojson")
        assert response.status_code == 200
        data = response.json()
        assert len(data["features"]) == 1

    def test_retrieve_own_gcp(
        self,
        service_user_api_client,
        workspace_factory,
        image_factory,
        ground_control_point_factory,
    ):
        user_workspace = workspace_factory(user_id=999)
        user_image = image_factory(workspace=user_workspace)
        gcp = ground_control_point_factory(image=user_image)

        response = service_user_api_client.get(f"/gcps/{gcp.uuid}")
        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == str(gcp.uuid)
        assert data["image_uuid"] == str(user_image.uuid)
        assert "created_at" in data

    def test_cannot_access_others_gcp(
        self,
        service_user_api_client,
        workspace_factory,
        image_factory,
        ground_control_point_factory,
    ):
        other_workspace = workspace_factory(user_id=456)
        other_image = image_factory(workspace=other_workspace)
        other_gcp = ground_control_point_factory(image=other_image)

        response = service_user_api_client.get(f"/gcps/{other_gcp.uuid}")
        assert response.status_code in (403, 404)

    def test_create_gcp_for_own_image(
        self,
        service_user_api_client,
        workspace_factory,
        image_factory,
    ):
        user_workspace = workspace_factory(user_id=999)
        user_image = image_factory(workspace=user_workspace)

        payload = {
            "gcp_point": [12.34, 56.78, 100.0],
            "image_point": [500.0, 300.0],
            "label": "GCP-USER-001",
        }
        response = service_user_api_client.post(
            f"/gcps/?image_uuid={user_image.uuid}",
            json=payload,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["label"] == "GCP-USER-001"
        assert data["image_uuid"] == str(user_image.uuid)

    def test_cannot_create_gcp_for_others_image(
        self,
        service_user_api_client,
        workspace_factory,
        image_factory,
    ):
        other_workspace = workspace_factory(user_id=456)
        other_image = image_factory(workspace=other_workspace)

        payload = {
            "gcp_point": [12.34, 56.78, 100.0],
            "image_point": [500.0, 300.0],
            "label": "GCP-FORBIDDEN",
        }
        response = service_user_api_client.post(
            f"/gcps/?image_uuid={other_image.uuid}",
            json=payload,
        )
        assert response.status_code in (403, 404)

    def test_update_own_gcp(
        self,
        service_user_api_client,
        workspace_factory,
        image_factory,
        ground_control_point_factory,
    ):
        user_workspace = workspace_factory(user_id=999)
        user_image = image_factory(workspace=user_workspace)
        gcp = ground_control_point_factory(image=user_image, label="old-label")

        payload = {"label": "updated-label"}
        response = service_user_api_client.patch(
            f"/gcps/{gcp.uuid}",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "updated-label"

    def test_cannot_update_others_gcp(
        self,
        service_user_api_client,
        workspace_factory,
        image_factory,
        ground_control_point_factory,
    ):
        other_workspace = workspace_factory(user_id=456)
        other_image = image_factory(workspace=other_workspace)
        other_gcp = ground_control_point_factory(image=other_image)

        payload = {"label": "hacked"}
        response = service_user_api_client.patch(
            f"/gcps/{other_gcp.uuid}",
            json=payload,
        )
        assert response.status_code in (403, 404)

    def test_delete_own_gcp(
        self,
        service_user_api_client,
        workspace_factory,
        image_factory,
        ground_control_point_factory,
    ):
        user_workspace = workspace_factory(user_id=999)
        user_image = image_factory(workspace=user_workspace)
        gcp = ground_control_point_factory(image=user_image)

        response = service_user_api_client.delete(f"/gcps/{gcp.uuid}")
        assert response.status_code == 204
        assert not GroundControlPoint.objects.filter(pk=gcp.pk).exists()

    def test_cannot_delete_others_gcp(
        self,
        service_user_api_client,
        workspace_factory,
        image_factory,
        ground_control_point_factory,
    ):
        other_workspace = workspace_factory(user_id=456)
        other_image = image_factory(workspace=other_workspace)
        other_gcp = ground_control_point_factory(image=other_image)

        response = service_user_api_client.delete(f"/gcps/{other_gcp.uuid}")
        assert response.status_code in (403, 404)
        assert GroundControlPoint.objects.filter(pk=other_gcp.pk).exists()


@pytest.mark.django_db
class TestGCPAPIUnauthorized:

    @pytest.mark.parametrize(
        "method, url, payload",
        [
            ("get", "/gcps/", None),
            ("get", "/gcps/geojson", None),
            ("get", "/gcps/{uuid}", None),
            ("post", "/gcps/?image_uuid={image_uuid}", {
                "gcp_point": [0, 0, 0],
                "image_point": [0, 0],
                "label": "test"
            }),
            ("patch", "/gcps/{uuid}", {"label": "test"}),
            ("delete", "/gcps/{uuid}", None),
        ],
    )
    def test_public_gcps_access_denied(
        self,
        api_client,
        ground_control_point_factory,
        method,
        url,
        payload,
    ):
        gcp = ground_control_point_factory()
        url = url.format(uuid=gcp.uuid, image_uuid=gcp.image.uuid)
        resp = getattr(api_client, method)(url, json=payload)
        assert resp.status_code in (401, 403)

    @pytest.mark.parametrize(
        "method, url, payload",
        [
            ("get", "/internal/gcps/", None),
            ("get", "/internal/gcps/{uuid}", None),
            ("post", "/internal/gcps/?image_uuid={image_uuid}", {
                "gcp_point": [0, 0, 0],
                "image_point": [0, 0],
                "label": "test"
            }),
            ("patch", "/internal/gcps/{uuid}", {"label": "test"}),
            ("delete", "/internal/gcps/{uuid}", None),
        ],
    )
    def test_internal_gcps_access_denied(
        self,
        api_client,
        ground_control_point_factory,
        method,
        url,
        payload,
    ):
        gcp = ground_control_point_factory()
        url = url.format(uuid=gcp.uuid, image_uuid=gcp.image.uuid)
        resp = getattr(api_client, method)(url, json=payload)
        assert resp.status_code in (401, 403)

    def test_jwt_user_cannot_access_internal_endpoints(
        self,
        service_user_api_client,
        ground_control_point_factory,
    ):
        gcp = ground_control_point_factory()
        response = service_user_api_client.get("/internal/gcps/")
        assert response.status_code in (401, 403)

        response = service_user_api_client.get(f"/internal/gcps/{gcp.uuid}")
        assert response.status_code in (401, 403)
