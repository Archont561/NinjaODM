import pytest
from pathlib import Path
from datetime import timedelta
from django.utils import timezone
from ninja_extra.testing import TestClient

from app.api.models.image import Image
from app.api.controllers.image import ImageControllerInternal, ImageControllerPublic
from ..auth_clients import AuthStrategyEnum, AuthenticatedTestClient


@pytest.fixture
def images_list(workspace_factory, image_factory):
    now = timezone.now()
    user_ws = workspace_factory(user_id=999)
    other_ws1 = workspace_factory(user_id=1)
    other_ws2 = workspace_factory(user_id=2)

    def create_image(workspace, name, is_thumbnail, days_ago):
        return image_factory(
            workspace=workspace,
            name=name,
            is_thumbnail=is_thumbnail,
            created_at=now - timedelta(days=days_ago)
        )

    return [
        create_image(user_ws, "Image 1", True, 1), 
        create_image(user_ws, "Image 2", False, 2),
        create_image(other_ws1, "Image 3", True, 5), 
        create_image(other_ws1, "Image 4", False, 10), 
        create_image(other_ws2, "Image 5", True, 3),
        create_image(other_ws2, "Image 6", False, 7),
    ]


@pytest.mark.django_db
class TestImageAPIInternal:
    @classmethod
    def setup_method(cls):
        cls.client = AuthenticatedTestClient(
            ImageControllerInternal, auth=AuthStrategyEnum.service
        )

    @pytest.mark.parametrize(
        "query_format, expected_count",
        [
            ("", 6), 
            ("name=Image 1", 1),
            ("is_thumbnail=True", 3),
            ("is_thumbnail=False", 3),
            ("created_after={after}", 3),
            ("created_before={before}", 5),
            ("created_after={after}&created_before={before}", 2),
            ("name=Image&is_thumbnail=True", 3),
        ],
    )
    def test_list_images_filtering(
        self, images_list, query_format, expected_count
    ):
        now = timezone.now()
        after_date = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
        before_date = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
        query = query_format.format(after=after_date, before=before_date)
        url = "/" + f"?{query}" if query else ""
        response = self.client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == expected_count, f"Failed for query: {query}"

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

    @pytest.mark.parametrize(
        "query_format, expected_count",
        [
            ("", 2),
            ("name=Image 1", 1),
            ("is_thumbnail=True", 1),
            ("is_thumbnail=False", 1),
            ("created_after={after}",  2),
            ("created_before={before}", 1),
            ("created_after={after}&created_before={before}", 1),
            ("name=Image&is_thumbnail=True", 1),
        ],
    )
    def test_list_own_images_filtering(
        self, images_list, query_format, expected_count
    ):
        now = timezone.now()
        after_date = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
        before_date = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
        query = query_format.format(after=after_date, before=before_date)
        url = "/" + f"?{query}" if query else ""
        response = self.client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == expected_count, f"Failed for query: {query}"

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
