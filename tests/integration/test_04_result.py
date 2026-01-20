import pytest
from datetime import timedelta
from django.utils import timezone
from ninja_extra.testing import TestClient

from app.api.models.result import ODMTaskResult
from app.api.constants.odm import ODMTaskResultType
from app.api.constants.token import ShareToken
from app.api.controllers.result import ResultControllerInternal, ResultControllerPublic
from ..auth_clients import AuthStrategyEnum, AuthenticatedTestClient


@pytest.fixture
def results_list(workspace_factory, odm_task_result_factory):
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

    return [
        create_result(user_ws, ODMTaskResultType.ORTHOPHOTO_GEOTIFF, 7),
        create_result(user_ws, ODMTaskResultType.ORTHOPHOTO_GEOTIFF, 3),
        create_result(user_ws, ODMTaskResultType.POINT_CLOUD_PLY, 3),
        create_result(user_ws, ODMTaskResultType.POINT_CLOUD_PLY, 1),
        create_result(other_ws1, ODMTaskResultType.ORTHOPHOTO_GEOTIFF, 3),
        create_result(other_ws2, ODMTaskResultType.DTM, 1),
        create_result(other_ws2, ODMTaskResultType.REPORT, 8),
    ]


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestTaskResultAPIInternal:
    @classmethod
    def setup_method(cls):
        cls.client = AuthenticatedTestClient(
            ResultControllerInternal, auth=AuthStrategyEnum.service
        )

    @pytest.mark.skip(reason="Sometimes different number of features are filtered")
    @pytest.mark.parametrize(
        "query_format, expected_count",
        [
            ("", 7),
            (f"result_type={ODMTaskResultType.ORTHOPHOTO_GEOTIFF}", 3),
            (f"result_type={ODMTaskResultType.POINT_CLOUD_PLY}", 2),
            (f"result_type={ODMTaskResultType.DTM}", 0),
            ("created_after={after}", 5),
            ("created_before={before}", 5),
            (
                f"result_type={ODMTaskResultType.ORTHOPHOTO_GEOTIFF}&created_after={{after}}",
                2,
            ),
            (
                f"result_type={ODMTaskResultType.POINT_CLOUD_PLY}&created_before={{before}}",
                1,
            ),
        ],
    )
    def test_list_results_filtering(self, results_list, query_format, expected_count):
        now = timezone.now()
        after_date = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
        before_date = (now - timedelta(days=2)).isoformat().replace("+00:00", "Z")
        query = query_format.format(after=after_date, before=before_date)
        url = "/" + f"?{query}" if query else ""
        response = self.client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == expected_count, f"Failed for query: {query}"

    def test_retrieve_any_result(self, odm_task_result_factory):
        result = odm_task_result_factory()
        response = self.client.get(f"/{result.uuid}")
        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == str(result.uuid)

    def test_delete_any_result(self, odm_task_result_factory, temp_image_file):
        result = odm_task_result_factory(file=temp_image_file)
        response = self.client.delete(f"/{result.uuid}")
        assert response.status_code == 204
        assert not ODMTaskResult.objects.filter(pk=result.pk).exists()


@pytest.mark.django_db
@pytest.mark.usefixtures("mock_redis")
class TestTaskResultAPIPublic:
    @classmethod
    def setup_method(cls):
        cls.client = AuthenticatedTestClient(
            ResultControllerPublic, auth=AuthStrategyEnum.jwt
        )
        cls.anon_client = TestClient(ResultControllerPublic)

    @pytest.mark.skip(reason="Sometimes different number of features are filtered")
    @pytest.mark.parametrize(
        "query_format, expected_count",
        [
            ("", 4),
            (f"result_type={ODMTaskResultType.ORTHOPHOTO_GEOTIFF}", 2),
            (f"result_type={ODMTaskResultType.POINT_CLOUD_PLY}", 2),
            (f"result_type={ODMTaskResultType.DTM}", 0),
            ("created_after={after}", 3),
            ("created_before={before}", 3),
            (
                f"result_type={ODMTaskResultType.ORTHOPHOTO_GEOTIFF}&created_after={{after}}",
                1,
            ),
            (
                f"result_type={ODMTaskResultType.POINT_CLOUD_PLY}&created_before={{before}}",
                1,
            ),
        ],
    )
    def test_list_user_results_filtering(
        self, results_list, query_format, expected_count
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

    def test_retrieve_own_result(self, workspace_factory, odm_task_result_factory):
        user_workspace = workspace_factory(user_id="user_999")
        result = odm_task_result_factory(workspace=user_workspace)
        response = self.client.get(f"/{result.uuid}")
        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == str(result.uuid)
        assert data["workspace_uuid"] == str(user_workspace.uuid)

    def test_cannot_access_others_result(
        self, workspace_factory, odm_task_result_factory
    ):
        other_workspace = workspace_factory(user_id="user_3243")
        other_result = odm_task_result_factory(workspace=other_workspace)
        response = self.client.get(f"/{other_result.uuid}")
        assert response.status_code in (403, 404)

    def test_delete_own_result(
        self, workspace_factory, odm_task_result_factory, temp_image_file
    ):
        user_workspace = workspace_factory(user_id="user_999")
        result = odm_task_result_factory(workspace=user_workspace, file=temp_image_file)
        response = self.client.delete(f"/{result.uuid}")
        assert response.status_code == 204
        assert not ODMTaskResult.objects.filter(pk=result.pk).exists()

    def test_download_own_result(
        self, workspace_factory, odm_task_result_factory, temp_image_file
    ):
        user_workspace = workspace_factory(user_id="user_999")
        result = odm_task_result_factory(workspace=user_workspace, file=temp_image_file)
        response = self.client.get(f"/{result.uuid}/download")
        assert response.status_code == 200
        assert response["Content-Type"] == "image/jpeg"
        assert "attachment" in response["Content-Disposition"]
        assert 'filename="test.jpg"' in response["Content-Disposition"]
        temp_image_file.seek(0)
        assert response.content == temp_image_file.read()

    def test_cannot_download_others_result_file(
        self, workspace_factory, odm_task_result_factory, temp_image_file
    ):
        other_workspace = workspace_factory(user_id="user_12345")
        result = odm_task_result_factory(
            workspace=other_workspace, file=temp_image_file
        )
        response = self.client.get(f"/{result.uuid}/download")
        assert response.status_code in (403, 404)

    def test_get_share_api_key(self, workspace_factory, odm_task_result_factory):
        user_workspace = workspace_factory(user_id="user_999")
        result = odm_task_result_factory(workspace=user_workspace)
        response = self.client.get(f"/{result.uuid}/share")
        assert response.status_code == 200
        token = ShareToken(response.json()["share_api_key"], verify=False)
        assert token["token_type"] == "share"
        assert token["result_uuid"] == str(result.uuid)
        assert token["shared_by_user_id"] == "user_999"

    def test_download_shared_result(
        self, workspace_factory, odm_task_result_factory, temp_image_file
    ):
        user_workspace = workspace_factory(user_id="user_999")
        result = odm_task_result_factory(workspace=user_workspace, file=temp_image_file)
        share_token = ShareToken.for_result(result)
        response = self.anon_client.get(f"/{result.uuid}/shared?api_key={share_token}")
        assert response.status_code == 200
        assert response["Content-Type"] == "image/jpeg"
        assert "attachment" in response["Content-Disposition"]
        assert 'filename="test.jpg"' in response["Content-Disposition"]
        temp_image_file.seek(0)
        assert response.content == temp_image_file.read()

    def test_cannot_download_non_shared_result_file(
        self, workspace_factory, odm_task_result_factory, temp_image_file
    ):
        user_workspace = workspace_factory(user_id="user_999")
        result = odm_task_result_factory(workspace=user_workspace)
        other_result = odm_task_result_factory(workspace=user_workspace)
        other_result_share_token = ShareToken.for_result(other_result)
        response = self.anon_client.get(
            f"/{result.uuid}/shared?api_key={other_result_share_token}"
        )
        assert response.status_code in (403, 404)


@pytest.mark.django_db
class TestTaskResultAPIUnauthorized:
    @classmethod
    def setup_method(cls):
        cls.public_client = TestClient(ResultControllerPublic)
        cls.internal_client = TestClient(ResultControllerInternal)
        cls.user_client = AuthenticatedTestClient(
            ResultControllerInternal, auth=AuthStrategyEnum.jwt
        )

    @pytest.mark.parametrize(
        "method, client_attr, url_template",
        [
            ("get", "public_client", "/"),
            ("get", "public_client", "/{uuid}"),
            ("delete", "public_client", "/{uuid}"),
            ("get", "internal_client", "/"),
            ("get", "internal_client", "/{uuid}"),
            ("delete", "internal_client", "/{uuid}"),
            ("get", "user_client", "/"),
            ("get", "user_client", "/{uuid}"),
            ("delete", "user_client", "/{uuid}"),
        ],
    )
    def test_access_denied(
        self, odm_task_result_factory, method, client_attr, url_template
    ):
        result = odm_task_result_factory()
        client = getattr(self, client_attr)
        url = url_template.format(uuid=result.uuid)
        response = getattr(client, method)(url)
        assert response.status_code in (401, 403)
        if method == "delete":
            assert ODMTaskResult.objects.filter(pk=result.pk).exists()
