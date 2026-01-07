import pytest
from pathlib import Path
from ninja_extra.testing import TestClient

from app.api.models.image import Image
from app.api.controllers.image import ImageControllerInternal, ImageControllerPublic
from ..auth_clients import AuthStrategyEnum, AuthenticatedTestClient


@pytest.mark.django_db
class TestImageAPIInternal:
    @classmethod
    def setup_method(cls):
        cls.client = AuthenticatedTestClient(
            ImageControllerInternal, auth=AuthStrategyEnum.service
        )

    def test_list_internal_images(self, image_factory):
        image_factory.create_batch(4)
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4

    def test_retrieve_any_image(self, image_factory):
        image = image_factory()
        response = self.client.get(f"/{image.uuid}")
        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == str(image.uuid)

    def test_delete_any_image(self, image_factory, temp_image_file):
        image = image_factory(image_file=temp_image_file)
        response = self.client.delete(f"/{image.uuid}")
        assert response.status_code == 204
        assert not Image.objects.filter(pk=image.pk).exists()
        file_path = Path(image.image_file.path)
        assert not file_path.exists()


@pytest.mark.django_db
class TestImageAPIPublic:
    @classmethod
    def setup_method(cls):
        cls.client = AuthenticatedTestClient(
            ImageControllerPublic, auth=AuthStrategyEnum.jwt
        )

    def test_list_user_images_only(self, workspace_factory, image_factory):
        user_workspace = workspace_factory(user_id=999)
        other_workspace = workspace_factory(user_id=123)
        user_images = image_factory.create_batch(3, workspace=user_workspace)
        image_factory.create_batch(2, workspace=other_workspace)

        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(user_images)
        returned_uuids = {item["uuid"] for item in data}
        expected_uuids = {str(img.uuid) for img in user_images}
        assert returned_uuids == expected_uuids

    def test_retrieve_own_image(self, workspace_factory, image_factory):
        user_workspace = workspace_factory(user_id=999)
        image = image_factory(workspace=user_workspace)
        response = self.client.get(f"/{image.uuid}")
        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == str(image.uuid)
        assert data["workspace_uuid"] == str(user_workspace.uuid)

    def test_cannot_access_others_image(self, workspace_factory, image_factory):
        other_workspace = workspace_factory(user_id=3243)
        other_image = image_factory(workspace=other_workspace)
        response = self.client.get(f"/{other_image.uuid}")
        assert response.status_code in (403, 404)

    def test_delete_own_image(self, workspace_factory, image_factory, temp_image_file):
        user_workspace = workspace_factory(user_id=999)
        image = image_factory(workspace=user_workspace, image_file=temp_image_file)
        response = self.client.delete(f"/{image.uuid}")
        assert response.status_code == 204
        assert not Image.objects.filter(pk=image.pk).exists()
        file_path = Path(image.image_file.path)
        assert not file_path.exists()

    def test_download_own_image_file(self, workspace_factory, image_factory, temp_image_file):
        user_workspace = workspace_factory(user_id=999)
        image = image_factory(
            workspace=user_workspace,
            image_file=temp_image_file
        )
        response = self.client.get(f"/{image.uuid}/download")
        assert response.status_code == 200
        assert response["Content-Type"] == "image/jpeg"
        assert 'attachment' in response["Content-Disposition"]
        assert 'filename="test.jpg"' in response["Content-Disposition"]
        temp_image_file.seek(0)
        assert response.content == temp_image_file.read()

    def test_cannot_download_others_image_file(self, workspace_factory, image_factory, temp_image_file):
        other_workspace = workspace_factory(user_id=12345)
        image = image_factory(
            workspace=other_workspace,
            image_file=temp_image_file
        )
        response = self.client.get(f"/{image.uuid}/download")
        assert response.status_code in (403, 404)


@pytest.mark.django_db
class TestImageAPIUnauthorized:
    @classmethod
    def setup_method(cls):
        cls.public_client = TestClient(ImageControllerPublic)
        cls.internal_client = TestClient(ImageControllerInternal)
        cls.user_client = AuthenticatedTestClient(
            ImageControllerInternal, auth=AuthStrategyEnum.jwt
        )

    @pytest.mark.parametrize(
        "method, client_attr, url_template",
        [
            ("get", "public_client", "/"),
            ("get", "public_client", "/{uuid}"),
            ("get", "internal_client", "/"),
            ("get", "internal_client", "/{uuid}"),
            ("delete", "internal_client", "/{uuid}"),
            ("get", "user_client", "/"),
            ("get", "user_client", "/{uuid}"),
            ("delete", "user_client", "/{uuid}"),
        ],
    )
    def test_access_denied(self, image_factory, method, client_attr, url_template):
        image = image_factory()
        client = getattr(self, client_attr)
        url = url_template.format(uuid=image.uuid)
        response = getattr(client, method)(url)
        assert response.status_code in (401, 403)
        if method == "delete":
            assert Image.objects.filter(pk=image.pk).exists()
