from typing import Any, Dict, List, Optional

from app.api.models.workspace import Workspace


class WorkspaceService:

    def list_all(self) -> List[Workspace]:
        return list(Workspace.objects.all())

    def list_for_user(self, user_id: int) -> List[Workspace]:
        return list(Workspace.objects.filter(user_id=user_id))

    def create_workspace(self, payload: Dict[str, Any]) -> Workspace:
        return Workspace.objects.create(**payload)

    def update_workspace(
        self,
        workspace: Workspace,
        payload: Dict[str, Any],
    ) -> Workspace:

        for field, value in payload.items():
            setattr(workspace, field, value)

        workspace.save()
        return workspace

    def delete_workspace(self, workspace: Workspace) -> None:
        workspace.delete()
