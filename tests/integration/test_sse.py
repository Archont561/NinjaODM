import pytest
import pytest_asyncio
import asyncio
from asgiref.sync import sync_to_async
from django.test import AsyncClient
from ninja_extra.testing import TestClient as NinjaExtraTestClient

from app.api.controllers.workspace import WorkspaceControllerPublic


@pytest_asyncio.fixture(scope="function")
async def api_sse_public_client(valid_token, mock_redis):
    client = AsyncClient()
    
    class SSEConnection:
        def __init__(self, response):
            self.response = response
            self.iterator = response.streaming_content.__aiter__()

        async def next_event(self, timeout=2.0):
            """Helper to get the next data event with a timeout."""
            return await asyncio.wait_for(self.iterator.__anext__(), timeout=timeout)

    response = await client.get(
        "/api/events", 
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    
    assert response.status_code == 200, f"SSE Auth failed: {response.content}"
    
    conn = SSEConnection(response)
    
    heartbeat = await conn.next_event()
    assert b": ok" in heartbeat
    return conn


@pytest.mark.django_db
@pytest.mark.asyncio
class TestSSEAPIPublic:
    async def test_workspace_creation_triggers_sse_event(self, api_sse_public_client, valid_token):
        client = NinjaExtraTestClient(WorkspaceControllerPublic)
        response = await sync_to_async(client.post)(
            "/", 
            headers={"Authorization": f"Bearer {valid_token}"}, 
            json={"name": "New Workspace"},
        )
        assert response.status_code == 201

        try:
            event_line = await api_sse_public_client.next_event()
            data = event_line.decode()
            
            assert "workspace:created" in data
            assert "New Workspace" in data
        except asyncio.TimeoutError:
            pytest.fail("The SSE client did not receive the workspace:created event.")
