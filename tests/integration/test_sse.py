import pytest
import pytest_asyncio
import asyncio
from asgiref.sync import sync_to_async
from django.test import AsyncClient

from app.api.controllers.workspace import WorkspaceControllerPublic
from ..auth_clients import AuthenticatedTestClient, AuthStrategyEnum


class SetupStrategy:
    async def none(factory):
        return None

    async def create_one(factory):
        return await sync_to_async(factory)(name="Test Workspace", user_id=999)


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


class SSEListener:
    def __init__(self, response):
        self.iterator = response.streaming_content.__aiter__()

    async def next_event(self, timeout: int = 2) -> str:
        try:
            chunk = await asyncio.wait_for(self.iterator.__anext__(), timeout=timeout)
            print(chunk)
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
    