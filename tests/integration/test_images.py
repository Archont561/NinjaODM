import pytest
from pathlib import Path

from app.api.models.image import Image


@pytest.mark.django_db
class TestImageAPIInternal:
    def test_list_internal_images(self, service_api_client, image_factory):
        image_factory.create_batch(4)
        response = service_api_client.get("/internal/images/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4

    def test_retrieve_any_image(self, service_api_client, image_factory):
        image = image_factory()
        response = service_api_client.get(f"/internal/images/{image.uuid}")
        assert response.status_code == 200
        assert response.json()["uuid"] == str(image.uuid)

    def test_delete_any_image(self, service_api_client, image_factory, temp_image_file):
        image = image_factory(image_file=temp_image_file)
        response = service_api_client.delete(f"/internal/images/{image.uuid}")
        assert response.status_code == 204
        assert not Image.objects.filter(pk=image.pk).exists()
        file_path = Path(image.image_file.path)
        assert not file_path.exists()


@pytest.mark.django_db
class TestImageAPIPublic:
    def test_list_user_images_only(
        self, service_user_api_client, workspace_factory, image_factory
    ):
        user_workspace = workspace_factory(user_id=999)
        other_workspace = workspace_factory(user_id=123)
        user_images = image_factory.create_batch(3, workspace=user_workspace)
        image_factory.create_batch(2, workspace=other_workspace)
        response = service_user_api_client.get("/images/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(user_images)
        returned_uuids = {item["uuid"] for item in data}
        expected_uuids = {str(img.uuid) for img in user_images}
        assert returned_uuids == expected_uuids

    def test_retrieve_own_image(
        self, service_user_api_client, workspace_factory, image_factory
    ):
        user_workspace = workspace_factory(user_id=999)
        image = image_factory(workspace=user_workspace)
        response = service_user_api_client.get(f"/images/{image.uuid}")
        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == str(image.uuid)
        assert data["workspace_uuid"] == str(user_workspace.uuid)

    def test_cannot_access_others_image(
        self, service_user_api_client, workspace_factory, image_factory
    ):
        other_workspace = workspace_factory(user_id=3243)
        other_image = image_factory(workspace=other_workspace)
        response = service_user_api_client.get(f"/images/{other_image.uuid}")
        assert response.status_code in (403, 404)

    def test_delete_own_image(
        self, service_user_api_client, workspace_factory, image_factory, temp_image_file
    ):
        user_workspace = workspace_factory(user_id=999)
        image = image_factory(workspace=user_workspace, image_file=temp_image_file)
        response = service_user_api_client.delete(f"/images/{image.uuid}")
        assert response.status_code == 204
        assert not Image.objects.filter(pk=image.pk).exists()
        file_path = Path(image.image_file.path)
        assert not file_path.exists()


@pytest.mark.django_db
class TestImageAPIUnauthorized:
    @pytest.mark.parametrize(
        "method, url, payload",
        [
            ("get", "/images/", None),
            ("get", "/images/{uuid}", None),
            ("delete", "/images/{uuid}", None),
        ],
    )
    def test_public_images_access_denied(
        self, api_client, image_factory, method, url, payload
    ):
        image = image_factory()
        url = url.format(uuid=image.uuid)
        resp = getattr(api_client, method)(url, json=payload)
        assert resp.status_code in (401, 403)

    @pytest.mark.parametrize(
        "method, url, payload",
        [
            ("get", "/internal/images/", None),
            ("get", "/internal/images/{uuid}", None),
            ("delete", "/internal/images/{uuid}", None),
        ],
    )
    def test_internal_images_access_denied(
        self, api_client, image_factory, method, url, payload
    ):
        image = image_factory()
        url = url.format(uuid=image.uuid)
        resp = getattr(api_client, method)(url, json=payload)
        assert resp.status_code in (401, 403)
