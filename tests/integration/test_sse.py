import pytest
import pytest_asyncio
import asyncio
from asgiref.sync import sync_to_async
from django.test import AsyncClient

from app.api.controllers.workspace import WorkspaceControllerPublic
from app.api.controllers.task import TaskControllerPublic
from app.api.controllers.gcp import GCPControllerPublic 
from app.api.controllers.image import ImageControllerPublic 
from app.api.controllers.result import ResultControllerPublic
from app.api.constants.odm import ODMTaskStatus
from ..auth_clients import AuthenticatedTestClient, AuthStrategyEnum


WORKSPACE_ACTIONS = {
    "create": lambda client, obj, payload, **kwargs: client.post("/", json=payload),
    "update": lambda client, obj, payload, **kwargs: client.patch(f"/{obj.uuid}", json=payload),
    "delete": lambda client, obj, payload, **kwargs: client.delete(f"/{obj.uuid}"),
    "upload_image": lambda client, obj, payload, file_obj=None, **kwargs: client.post(
        f"/{obj.uuid}/upload-image", FILES={"image_file": file_obj}
    ),
}

TASK_ACTIONS = {
    "pause": lambda client, obj, **kwargs: client.post(f"/{obj.uuid}/pause"),
    "resume": lambda client, obj, **kwargs: client.post(f"/{obj.uuid}/resume"),
    "cancel": lambda client, obj, **kwargs: client.post(f"/{obj.uuid}/cancel"),
    "delete": lambda client, obj, **kwargs: client.delete(f"/{obj.uuid}"),
}

GCP_ACTIONS = {
    "create": lambda client, obj, payload, **kwargs: client.post(f"/?image_uuid={kwargs.get('image_uuid')}", json=payload),
    "update": lambda client, obj, payload, **kwargs: client.patch(f"/{obj.uuid}", json=payload),
    "delete": lambda client, obj, payload, **kwargs: client.delete(f"/{obj.uuid}"),
}


class SSEListener:
    """Helper to parse SSE stream events."""
    def __init__(self, response):
        self.iterator = response.streaming_content.__aiter__()

    async def next_event(self, timeout: int = 2) -> str:
        try:
            chunk = await asyncio.wait_for(self.iterator.__anext__(), timeout=timeout)
            return chunk.decode("utf-8")
        except (StopAsyncIteration, asyncio.TimeoutError):
            raise TimeoutError("SSE Stream stopped or timed out.")


@pytest.mark.django_db
@pytest.mark.asyncio
class TestSSEAPIPublic:

    @pytest.fixture
    def workspace_client(self):
        return AuthenticatedTestClient(WorkspaceControllerPublic, auth=AuthStrategyEnum.jwt)

    @pytest.fixture
    def task_client(self):
        return AuthenticatedTestClient(TaskControllerPublic, auth=AuthStrategyEnum.jwt)

    @pytest.fixture
    def gcp_client(self):
        return AuthenticatedTestClient(GCPControllerPublic, auth=AuthStrategyEnum.jwt)

    @pytest_asyncio.fixture
    async def sse_listener(self, valid_token, mock_redis):
        client = AsyncClient()
        response = await client.get(
            "/api/events", headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        
        listener = SSEListener(response)
        
        heartbeat = await listener.next_event()
        assert ": ok" in heartbeat
        
        yield listener
        
        response.close()

    async def _run_lifecycle_test(
        self,
        client,
        action_func,
        listener,
        target_obj=None,
        payload=None,
        expected_status=200,
        expected_event_key=None,
        **kwargs
    ):
        """
        Executes an action and asserts that the expected SSE event was emitted.
        """
        response = await sync_to_async(action_func)(
            client=client, 
            obj=target_obj, 
            payload=payload, 
            **kwargs
        )
        assert response.status_code == expected_status, f"API Error: {response.content}"

        try:
            event_data = await listener.next_event()
            assert expected_event_key in event_data
            
            if target_obj and hasattr(target_obj, 'uuid'):
                assert str(target_obj.uuid) in event_data
        except TimeoutError as e:
            pytest.fail(f"SSE Verification Failed for {expected_event_key}: {e}")

    @pytest.mark.parametrize(
        "action_key, payload, event_type, expected_status",
        [
            ("create", {"name": "New"}, "workspace:created", 201),
            ("update", {"name": "Upd"}, "workspace:updated", 200),
            ("delete", None, "workspace:deleted", 204),
            ("upload_image", None, "workspace:images-uploaded", 200),
        ]
    )
    async def test_workspace_lifecycle(
        self, workspace_client, sse_listener, workspace_factory, temp_image_file, 
        action_key, payload, event_type, expected_status,
    ):
        workspace = None
        if action_key != "create":
            workspace = await sync_to_async(workspace_factory)(name="Test Workspace", user_id=999)

        await self._run_lifecycle_test(
            client=workspace_client,
            target_obj=workspace,
            action_func=WORKSPACE_ACTIONS[action_key],
            listener=sse_listener,
            payload=payload,
            expected_status=expected_status,
            expected_event_key=event_type,
            file_obj=temp_image_file if action_key == "upload_image" else None
        )

    @pytest.mark.parametrize(
        "action_key, payload, event_type, expected_status",
        [
            ("pause", None, "task:updated", 200),
            ("resume", None, "task:updated", 200),
            ("cancel", None, "task:updated", 200),
            ("delete", None, "task:deleted", 204),
        ]
    )
    async def test_odm_task_lifecycle(
        self, task_client, sse_listener, odm_task_factory, workspace_factory,
        action_key, payload, event_type, expected_status
    ):
        user_workspace = await sync_to_async(workspace_factory)(user_id=999)
        odm_task = await sync_to_async(odm_task_factory)(
            workspace=user_workspace, status=ODMTaskStatus.COMPLETED
        )

        await self._run_lifecycle_test(
            client=task_client,
            target_obj=odm_task,
            action_func=TASK_ACTIONS[action_key],
            listener=sse_listener,
            payload=payload,
            expected_status=expected_status,
            expected_event_key=event_type
        )

    @pytest.mark.parametrize(
        "action_key, payload, event_type, expected_status",
        [
            ("create", {
                "gcp_point": [12.34, 56.78, 100.0],
                "image_point": [500.0, 300.0],
                "label": "New",
            }, "gcp:created", 201),
            ("update", {"label": "Upd"}, "gcp:updated", 200),
            ("delete", None, "gcp:deleted", 204),
        ]
    )
    async def test_gcp_lifecycle(
        self, gcp_client, sse_listener, 
        workspace_factory, image_factory, ground_control_point_factory,
        action_key, payload, event_type, expected_status
    ):
        gcp = None
        kwargs = {}
        user_workspace = await sync_to_async(workspace_factory)(user_id=999)
        image = await sync_to_async(image_factory)(workspace=user_workspace)

        if action_key == "create":
            kwargs["image_uuid"] = image.uuid
        else:
            gcp = await sync_to_async(ground_control_point_factory)(image=image)

        await self._run_lifecycle_test(
            client=gcp_client,
            target_obj=gcp,
            action_func=GCP_ACTIONS[action_key],
            listener=sse_listener,
            payload=payload,
            expected_status=expected_status,
            expected_event_key=event_type,
            **kwargs
        )
