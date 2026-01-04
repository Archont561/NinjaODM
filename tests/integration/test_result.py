import pytest

from app.api.models.result import ODMTaskResult
from app.api.constants.odm import ODMTaskResultType


@pytest.mark.django_db
class TestTaskResultAPIInternal:
    def test_list_internal_results(
        self,
        service_api_client,
        odm_task_result_factory,
        workspace_factory,
    ):
        odm_task_result_factory.create_batch(4)
        response = service_api_client.get("/internal/results/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4

    def test_retrieve_any_result(
        self,
        service_api_client,
        odm_task_result_factory,
    ):
        result = odm_task_result_factory()
        response = service_api_client.get(f"/internal/results/{result.uuid}")
        assert response.status_code == 200
        assert response.json()["uuid"] == str(result.uuid)

    def test_delete_any_result(
        self,
        service_api_client,
        odm_task_result_factory,
        workspace_factory,
    ):
        result = odm_task_result_factory()
        response = service_api_client.delete(f"/internal/results/{result.uuid}")
        assert response.status_code == 204
        assert not ODMTaskResult.objects.filter(pk=result.pk).exists()


@pytest.mark.django_db
class TestTaskResultAPIPublic:
    def test_list_user_results_only(
        self,
        service_user_api_client,
        workspace_factory,
        odm_task_result_factory,
    ):
        user_workspace = workspace_factory(user_id=999)
        other_workspace = workspace_factory(user_id=123)
        result1 = odm_task_result_factory(workspace=user_workspace)
        odm_task_result_factory(workspace=other_workspace)
        response = service_user_api_client.get("/results/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["uuid"] == str(result1.uuid)

    def test_retrieve_own_result(
        self,
        service_user_api_client,
        workspace_factory,
        odm_task_result_factory,
    ):
        user_workspace = workspace_factory(user_id=999)
        result = odm_task_result_factory(workspace=user_workspace)
        response = service_user_api_client.get(f"/results/{result.uuid}")
        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == str(result.uuid)
        assert data["workspace_uuid"] == str(user_workspace.uuid)

    def test_cannot_access_others_result(
        self,
        service_user_api_client,
        workspace_factory,
        odm_task_result_factory,
    ):
        other_workspace = workspace_factory(user_id=3243)
        other_result = odm_task_result_factory(workspace=other_workspace)
        response = service_user_api_client.get(f"/results/{other_result.uuid}")
        assert response.status_code in (403, 404)

    def test_delete_own_result(
        self,
        service_user_api_client,
        workspace_factory,
        odm_task_result_factory,
    ):
        user_workspace = workspace_factory(user_id=999)
        result = odm_task_result_factory(workspace=user_workspace)
        response = service_user_api_client.delete(f"/results/{result.uuid}")
        assert response.status_code == 204
        assert not ODMTaskResult.objects.filter(pk=result.pk).exists()

    
@pytest.mark.django_db
class TestTaskResultAPIUnauthorized:

    @pytest.mark.parametrize(
        "method, url, payload",
        [
            ("get", "/results/", None),
            ("get", "/results/{uuid}", None),
            ("delete", "/results/{uuid}", None),
        ],
    )
    def test_public_results_access_denied(
        self, api_client, odm_task_result_factory, method, url, payload
    ):
        result = odm_task_result_factory()
        url = url.format(uuid=result.uuid)
        resp = getattr(api_client, method)(url, json=payload)
        assert resp.status_code in (401, 403)

    @pytest.mark.parametrize(
        "method, url, payload",
        [
            ("get", "/internal/results/", None),
            ("get", "/internal/results/{uuid}", None),
            ("delete", "/internal/results/{uuid}", None),
        ],
    )
    def test_internal_results_access_denied(
        self, api_client, odm_task_result_factory, method, url, payload
    ):
        result = odm_task_result_factory()
        url = url.format(uuid=result.uuid)
        resp = getattr(api_client, method)(url, json=payload)
        assert resp.status_code in (401, 403)
    