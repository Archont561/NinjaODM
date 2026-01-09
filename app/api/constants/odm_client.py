from __future__ import annotations
from uuid import UUID
from pyodm import Node
from django.conf import settings

from app.api.auth.nodeodm import NodeODMServiceAuth


class NodeODMClient(Node):

    def __init__(self, uuid: UUID, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uuid = uuid
    
    @staticmethod
    def for_task(uuid: UUID, timeout: int=30) -> NodeODMClient:
        node = Node.from_url(settings.NODEODM_URL, timeout)
        return NodeODMClient(uuid, node.hostname, node.port, node.token, node.timeout)

    def post(self, url: str, data=None, headers={}):
        if url in ["/task/new/init", "/task/new"]:
            headers["set-uuid"] = str(self.uuid)
        super().post(url, data=data, headers=headers)

    def create_task(self, *args, **kwargs):
        expected_signature = NodeODMServiceAuth.generate_hmac_signature(NodeODMServiceAuth.HMAC_MESSAGE)
        kwargs["webhook"] = f"{settings.NINJAODM_BASE_URL}/api/internal/tasks/{self.uuid}/webhook?signature={expected_signature}"
        super().create_task(*args, **kwargs)
