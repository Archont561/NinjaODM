import pytest
import os
from uuid import uuid4
from unittest.mock import patch, MagicMock
from pyodm import Node
from pyodm.api import Task
from pyodm.types import NodeInfo, NodeOption, TaskInfo
from pyodm.exceptions import NodeConnectionError, NodeResponseError

from tests.server_mocks import NodeODMMockHTTPServer
from app.api.constants.odm_client import NodeODMClient
from app.api.auth.nodeodm import NodeODMServiceAuth


@pytest.fixture
def mock_odm_server(httpserver, settings):
    mock_server = NodeODMMockHTTPServer(httpserver).register_routes()
    settings.NODEODM_URL = mock_server.base_url
    settings.NINJAODM_BASE_URL = "https://ninjaodm.example.com"
    return mock_server


@pytest.fixture
def task_uuid():
    return uuid4()


@pytest.fixture
def nodeodm_client(mock_odm_server, task_uuid):
    return NodeODMClient.for_task(task_uuid)


@pytest.fixture
def initialized_task(mock_odm_server, nodeodm_client):
    """Create and return an initialized task."""
    mock_odm_server.manager.create_init(str(nodeodm_client.uuid), "test", [])
    return nodeodm_client.get_task(str(nodeodm_client.uuid))


class TestNodeODMClient:
    def test_for_task_creates_client_with_correct_attributes(self, mock_odm_server, settings):
        from urllib.parse import urlparse
        
        test_uuid = uuid4()
        client = NodeODMClient.for_task(test_uuid, timeout=120)
        parsed = urlparse(settings.NODEODM_URL)
        
        assert client.uuid == test_uuid
        assert client.host == parsed.hostname
        assert client.timeout == 120
        assert isinstance(client, Node)
        
    def test_info_returns_expected_data(self, nodeodm_client):
        info = nodeodm_client.info()
        
        assert isinstance(info, NodeInfo)
        assert info.version == "2.3.2"
        assert info.engine == "odm"
        assert info.cpu_cores == 4
        
    def test_options_returns_node_options(self, nodeodm_client):
        options = nodeodm_client.options()
        
        assert isinstance(options, list)
        assert all(isinstance(opt, NodeOption) for opt in options)
        assert any(opt.name == "dsm" for opt in options)
        
    @pytest.mark.parametrize("endpoint,should_inject", [
        ("/task/new/init", True),
        ("/task/new", True),
        ("/task/cancel", False),
    ])
    def test_uuid_header_injection(self, task_uuid, mock_odm_server, endpoint, should_inject):
        client = NodeODMClient.for_task(task_uuid)
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {'Content-Type': 'application/json'}
            mock_response.json.return_value = {'uuid': str(task_uuid), 'success': True}
            mock_post.return_value = mock_response
            
            client.post(endpoint, data={}, headers={})
            
            headers = mock_post.call_args.kwargs.get('headers', {})
            assert ('set-uuid' in headers) == should_inject
            
    def test_create_task_injects_webhook_with_signature(self, nodeodm_client, task_uuid, settings):
        expected_signature = NodeODMServiceAuth.generate_hmac_signature(
            NodeODMServiceAuth.HMAC_MESSAGE
        )
        
        with patch.object(Node, 'create_task') as mock_super:
            mock_super.return_value = MagicMock()
            nodeodm_client.create_task(['img.jpg'], options={'dsm': True}, name="Test")
            
            webhook = mock_super.call_args.kwargs['webhook']
            assert str(task_uuid) in webhook
            assert f"signature={expected_signature}" in webhook
            assert settings.NINJAODM_BASE_URL in webhook
        
    def test_get_task_returns_task_object(self, nodeodm_client):
        task = nodeodm_client.get_task(str(uuid4()))
        
        assert isinstance(task, Task)
        assert task.node == nodeodm_client

    def test_task_info(self, initialized_task):
        info = initialized_task.info()
        
        assert isinstance(info, TaskInfo)
        assert hasattr(info, 'status')

    def test_task_output(self, initialized_task):
        output = initialized_task.output()
        assert output is not None

    @pytest.mark.parametrize("action", ["cancel", "remove", "restart"])
    def test_task_control_actions(self, initialized_task, action):
        result = getattr(initialized_task, action)()
        assert result is True

    def test_task_control_on_nonexistent_task(self, nodeodm_client):
        task = nodeodm_client.get_task(str(uuid4()))
        assert task.cancel() is False
        
    def test_download_zip(self, mock_odm_server, initialized_task, tmp_path):
        mock_odm_server.manager.get_task(initialized_task.uuid).status.code = 40 # COMPLETED
        
        zip_path = initialized_task.download_zip(str(tmp_path))
        
        assert zip_path.endswith('.zip')
        assert os.path.exists(zip_path)

    def test_download_zip_fails_if_not_completed(self, initialized_task, tmp_path):
        with pytest.raises(NodeResponseError, match="Cannot download task"):
            initialized_task.download_zip(str(tmp_path))
            
    @pytest.mark.parametrize("version,expected", [
        ('1.4.0', True), ('2.3.2', True), ('10.0.0', False),
    ])
    def test_version_greater_or_equal_than(self, nodeodm_client, version, expected):
        assert nodeodm_client.version_greater_or_equal_than(version) is expected
        
    def test_connection_error_on_unreachable_host(self, settings):
        settings.NODEODM_URL = "http://nonexistent.invalid:9999"
        
        with pytest.raises(NodeConnectionError):
            NodeODMClient.for_task(uuid4(), timeout=1).info()

    def test_task_not_found_error(self, nodeodm_client):
        task = nodeodm_client.get_task(str(uuid4()))
        
        with pytest.raises(NodeResponseError, match="Task not found"):
            task.info()
