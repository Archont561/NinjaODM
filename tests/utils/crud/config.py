from __future__ import annotations

from typing import Iterator, Optional, ClassVar
from pydantic import Field

from .models import (
    Model,
    Ref,
    FnRef,
    BoolRef,
    StatusRef,
    CRUDConfig,
    CRUDScenario,
    ActionConfig,
    ActionScenario,
    ListConfig,
    ListScenario,
)
from .utils import merge_dicts


class TestConfig(Model):
    """
    Main test configuration.

    Inheritance chain: TestConfig → OperationConfig → Scenario

    Example:
        tests = {
            "model": Item,
            "endpoint": "/api/items/",
            "factory": "item_factory",
            "client": "auth_client",

            "cruds": {
                "create": {
                    "expected_status": 201,
                    "scenarios": [...]
                },
            },

            "actions": {
                "publish": {
                    "url": lambda r, obj: f"/{obj.uuid}/publish",
                    "method": "post",
                    "scenarios": [...]
                }
            },

            "list": {
                "queries": [
                    {"params": {"filter": "active"}, "expected_count": 5}
                ],
                "scenarios": [...]
            }
        }
    """

    # Required defaults
    model: Ref
    endpoint: str
    factory: FnRef
    client: Ref

    # Optional defaults
    assertion: Optional[FnRef] = Field(None, alias="assert")
    expected_status: Optional[StatusRef] = None
    access_denied: Optional[BoolRef] = None

    # HTTP defaults (optional)
    url: Optional[FnRef] = None
    method: Optional[str] = None
    payload: Optional[FnRef] = None
    files: Optional[FnRef] = None
    headers: Optional[Ref] = None
    query: Optional[Ref] = None

    # Operations
    cruds: dict[str, dict] = Field(default_factory=dict)
    actions: dict[str, dict] = Field(default_factory=dict)
    list: Optional[dict] = Field(None)

    # Class configuration
    _inherit_fields: ClassVar[set[str]] = {
        "model",
        "endpoint",
        "factory",
        "client",
        "assertion",
        "expected_status",
        "access_denied",
        "url",
        "method",
        "payload",
        "files",
        "headers",
        "query",
    }

    @property
    def defaults(self) -> dict:
        """Get inheritable defaults."""
        return self.model_dump(include=self._inherit_fields, exclude_none=True)

    def crud_items(self) -> Iterator[tuple[str, CRUDConfig, list[CRUDScenario]]]:
        """
        Iterate over CRUD operations with their configs and scenarios.

        Yields:
            Tuples of (operation_name, config, scenarios)
        """
        for op, data in self.cruds.items():
            # Merge TestConfig defaults → CRUD operation config
            config_data = merge_dicts(self.defaults, data)
            cfg = CRUDConfig(**config_data)

            # Get scenarios with merged defaults
            scenarios = cfg.get_scenarios(merge_dicts, self.defaults)

            yield op, cfg, scenarios

    def action_items(self) -> Iterator[tuple[str, ActionConfig, list[ActionScenario]]]:
        """
        Iterate over action operations with their configs and scenarios.

        Yields:
            Tuples of (action_name, config, scenarios)
        """
        for name, data in self.actions.items():
            # Merge TestConfig defaults → Action config
            config_data = merge_dicts(self.defaults, data)
            cfg = ActionConfig(**config_data)

            # Get scenarios with merged defaults
            scenarios = cfg.get_scenarios(merge_dicts, self.defaults)

            yield name, cfg, scenarios

    def list_items(self) -> Optional[tuple[ListConfig, list[ListScenario]]]:
        """
        Get list config and scenarios if defined.

        Returns:
            Tuple of (config, scenarios) or None if no list config
        """
        if not self.list:
            return None

        # Merge TestConfig defaults → List config
        config_data = merge_dicts(self.defaults, self.list)
        cfg = ListConfig(**config_data)

        # Get scenarios with merged defaults
        scenarios = cfg.get_scenarios(merge_dicts, self.defaults)

        return cfg, scenarios
