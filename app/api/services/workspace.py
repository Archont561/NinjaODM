import json
from ninja_extra import ModelService

from app.api.sse import emit_event


class WorkspaceModelService(ModelService):
    def create(self, schema, **kwargs):
        instance = super().create(schema, **kwargs)
        emit_event(instance.user_id, "workspace:created", {
            "uuid": str(instance.uuid),
            "name": instance.name
        })
        return instance
    
        