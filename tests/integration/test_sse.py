import pytest
import pytest_asyncio
import asyncio
from asgiref.sync import sync_to_async
from django.test import AsyncClient

from app.api.controllers.workspace import WorkspaceControllerPublic
from app.api.controllers.task import TaskControllerPublic
from app.api.constants.odm import ODMTaskStatus
from ..auth_clients import AuthenticatedTestClient, AuthStrategyEnum


class SetupStrategy:
    async def none(factory):
        return None

    async def create_one(factory):
        return await sync_to_async(factory)(name="Test Workspace", user_id=999)


class TaskSetupStrategy:
    async def create_one(factory, workspace_factory):
        user_workspace = await SetupStrategy.create_one(workspace_factory)
        return await sync_to_async(factory)(workspace=user_workspace, status=ODMTaskStatus.COMPLETED)


class RequestStrategy:
    def create(client, workspace, payload, **kwargs):
        return client.post("/", json=payload)

    def update(client, workspace, payload, **kwargs):
        return client.patch(f"/{workspace.uuid}", json=payload)

    def delete(client, workspace, payload, **kwargs):
        return client.delete(f"/{workspace.uuid}")
    
    def upload_image(client, workspace, payload, file_obj=None, **kwargs):
        return client.post(
            f"/{workspace.uuid}/upload-image",
            FILES={"image_file": file_obj}
        )

class TaskRequestStrategy:
    def create(client, odm_task, payload, **kwargs):
        return client.post("/", json=payload)

    def pause(client, odm_task, payload, **kwargs):
        return client.post(f"/{odm_task.uuid}/pause", json=payload)

    def resume(client, odm_task, payload, **kwargs):
        return client.post(f"/{odm_task.uuid}/resume")

    def cancel(client, odm_task, payload, **kwargs):
        return client.post(f"/{odm_task.uuid}/cancel")

    def delete(client, odm_task, payload, **kwargs):
        return client.delete(f"/{odm_task.uuid}")
    

class SSEListener:
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

    @classmethod
    def setup_method(cls):
        cls.workspace_client = AuthenticatedTestClient(
            WorkspaceControllerPublic, auth=AuthStrategyEnum.jwt
        )
        cls.task_client = AuthenticatedTestClient(
            TaskControllerPublic, auth=AuthStrategyEnum.jwt
        )

    @pytest_asyncio.fixture(autouse=True)
    async def setup_sse_context(self, valid_token, mock_redis):
        client = AsyncClient()
        response = await client.get(
            "/api/events", headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        self.sse_listener = SSEListener(response)
        
        # Heartbeat check
        heartbeat = await self.sse_listener.next_event()
        assert ": ok" in heartbeat
        
        yield
        response.close()

    @pytest.mark.parametrize(
        "setup_strat, request_strat, payload, event_type, expected_status",
        [
            # Case 1: Create
            (SetupStrategy.none, RequestStrategy.create, {"name": "New"}, "workspace:created", 201),
            
            # Case 2: Update
            (SetupStrategy.create_one, RequestStrategy.update, {"name": "Upd"}, "workspace:updated", 200),
            
            # Case 3: Delete
            (SetupStrategy.create_one, RequestStrategy.delete, None, "workspace:deleted", 204),
            
            # Case 4: Image Upload
            (SetupStrategy.create_one, RequestStrategy.upload_image, None, "workspace:images-uploaded", 200),
        ]
    )
    async def test_workspace_lifecycle_sse(
        self, 
        workspace_factory,
        temp_image_file,
        setup_strat, 
        request_strat, 
        payload, 
        event_type, 
        expected_status
    ):
        workspace = await setup_strat(workspace_factory)
        response = await sync_to_async(request_strat)(
            client=self.workspace_client, 
            workspace=workspace, 
            payload=payload, 
            file_obj=temp_image_file
        )
        assert response.status_code == expected_status
        try:
            event_data = await self.sse_listener.next_event()
            assert event_type in event_data
            if workspace:
                assert str(workspace.uuid) in event_data
        except TimeoutError as e:
            pytest.fail(f"SSE Verification Failed: {e}")
    
    @pytest.mark.parametrize(
        "setup_strat, request_strat, payload, event_type, expected_status",
        [
            (TaskSetupStrategy.create_one, TaskRequestStrategy.pause, None, "task:updated", 200),
            (TaskSetupStrategy.create_one, TaskRequestStrategy.resume, None, "task:updated", 200),
            (TaskSetupStrategy.create_one, TaskRequestStrategy.cancel, None, "task:updated", 200),
            (TaskSetupStrategy.create_one, TaskRequestStrategy.delete, None, "task:deleted", 204),
        ]
    )
    async def test_odm_task_lifecycle_sse(
        self, 
        odm_task_factory,
        workspace_factory,
        setup_strat, 
        request_strat, 
        payload, 
        event_type, 
        expected_status
    ):
        odm_task = await setup_strat(odm_task_factory, workspace_factory)
        print(odm_task)
        response = await sync_to_async(request_strat)(
            client=self.task_client, 
            odm_task=odm_task, 
            payload=payload, 
        )
        assert response.status_code == expected_status
        try:
            event_data = await self.sse_listener.next_event()
            assert event_type in event_data
            if odm_task:
                assert str(odm_task.uuid) in event_data
        except TimeoutError as e:
            pytest.fail(f"SSE Verification Failed: {e}")
