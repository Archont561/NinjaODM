import pytest
from ninja_extra.testing import TestClient

from app.api.models.result import ODMTaskResult
from app.api.controllers.result import ResultControllerInternal, ResultControllerPublic
from ..auth_clients import AuthStrategyEnum, AuthenticatedTestClient


@pytest.mark.django_db
class TestTaskResultAPIInternal:
    @classmethod
    def setup_method(cls):
        cls.client = AuthenticatedTestClient(
            ResultControllerInternal, auth=AuthStrategyEnum.service
        )

    def test_list_internal_results(self, odm_task_result_factory):
        odm_task_result_factory.create_batch(4)
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4

    def test_retrieve_any_result(self, odm_task_result_factory):
        result = odm_task_result_factory()
        response = self.client.get(f"/{result.uuid}")
        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == str(result.uuid)

    def test_delete_any_result(self, odm_task_result_factory):
        result = odm_task_result_factory()
        response = self.client.delete(f"/{result.uuid}")
        assert response.status_code == 204
        assert not ODMTaskResult.objects.filter(pk=result.pk).exists()


@pytest.mark.django_db
class TestTaskResultAPIPublic:
    @classmethod
    def setup_method(cls):
        cls.client = AuthenticatedTestClient(
            ResultControllerPublic, auth=AuthStrategyEnum.jwt
        )

    def test_list_user_results_only(self, workspace_factory, odm_task_result_factory):
        user_workspace = workspace_factory(user_id=999)
        other_workspace = workspace_factory(user_id=123)
        user_results = odm_task_result_factory.create_batch(2, workspace=user_workspace)
        odm_task_result_factory.create_batch(3, workspace=other_workspace)
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(user_results)
        returned_uuids = {item["uuid"] for item in data}
        expected_uuids = {str(result.uuid) for result in user_results}
        assert returned_uuids == expected_uuids

    def test_retrieve_own_result(self, workspace_factory, odm_task_result_factory):
        user_workspace = workspace_factory(user_id=999)
        result = odm_task_result_factory(workspace=user_workspace)
        response = self.client.get(f"/{result.uuid}")
        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == str(result.uuid)
        assert data["workspace_uuid"] == str(user_workspace.uuid)

    def test_cannot_access_others_result(
        self, workspace_factory, odm_task_result_factory
    ):
        other_workspace = workspace_factory(user_id=3243)
        other_result = odm_task_result_factory(workspace=other_workspace)
        response = self.client.get(f"/{other_result.uuid}")
        assert response.status_code in (403, 404)

    def test_delete_own_result(self, workspace_factory, odm_task_result_factory):
        user_workspace = workspace_factory(user_id=999)
        result = odm_task_result_factory(workspace=user_workspace)
        response = self.client.delete(f"/{result.uuid}")
        assert response.status_code == 204
        assert not ODMTaskResult.objects.filter(pk=result.pk).exists()


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
