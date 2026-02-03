from __future__ import annotations

import pytest
from functools import cached_property
from typing import Any, Optional, TYPE_CHECKING

from .config import TestConfig
from .utils import ResolverMixin
from .runners import CRUDRunner, ActionRunner, ListRunner, BaseRunner

if TYPE_CHECKING:
    from pytest_subtests import SubTests


class APITestSuite(ResolverMixin):
    """
    Declarative API test suite base class.

    Subclass this and define the `tests` dictionary to create a test suite.

    Usage:
        @pytest.mark.django_db
        class TestItemAPI(APITestSuite):
            tests = {
                "model": Item,
                "endpoint": "/api/items/",
                "factory": "item_factory",
                "client": "auth_client",
                "cruds": { ... },
                ...
            }
    """

    # Configuration dict (must be defined in subclass)
    tests: dict

    # Internal references
    _request: pytest.FixtureRequest
    _subtests: Optional[SubTests] = None

    @pytest.fixture(autouse=True)
    def _inject_fixtures(self, request: pytest.FixtureRequest, subtests):
        """
        Inject pytest request and subtests fixtures.

        Args:
            request: Standard pytest request
            subtests: Optional fixture from pytest-subtests plugin
        """
        self._request = request
        self._subtests = subtests

        # Clear cached config to ensure freshness per test if needed
        self.__dict__.pop("config", None)

        # Simple validation
        if not hasattr(self, "tests"):
            pytest.fail(
                f"Class {self.__class__.__name__} must define 'tests' dictionary"
            )

    @cached_property
    def config(self) -> TestConfig:
        """Parsed and validated test configuration."""
        return TestConfig(**self.tests)

    def _run_with_subtests(
        self, runner: BaseRunner, scenarios: list, config: Any, prefix: str = ""
    ) -> None:
        """
        Execute scenarios using subtests if available, otherwise standard loop.
        """
        for i, scenario in enumerate(scenarios):
            # Generate a readable ID for the test
            sid = runner.sid(scenario, i, prefix)

            if self._subtests:
                with self._subtests.test(msg=sid):
                    runner.run(scenario, i, config)
            else:
                # Fallback if pytest-subtests is not installed
                runner.run(scenario, i, config)

    # -------------------------
    # CRUD Tests
    # -------------------------

    def _run_crud_op(self, operation: str):
        """Generic helper for CRUD operations."""
        # Find the specific CRUD config and scenarios
        found = False
        for op, cfg, scenarios in self.config.crud_items():
            if op == operation:
                found = True
                runner = CRUDRunner(self, operation)
                self._run_with_subtests(runner, scenarios, cfg, prefix=operation)
                break

        if not found:
            pytest.skip(f"No '{operation}' scenarios configured")

    @pytest.mark.order(1)
    def test_create(self):
        """Test create scenarios."""
        self._run_crud_op("create")

    @pytest.mark.order(2)
    def test_get(self):
        """Test get scenarios."""
        self._run_crud_op("get")

    @pytest.mark.order(3)
    def test_update(self):
        """Test update scenarios."""
        self._run_crud_op("update")

    @pytest.mark.order(4)
    def test_delete(self):
        """Test delete scenarios."""
        self._run_crud_op("delete")

    # -------------------------
    # Action Tests
    # -------------------------

    @pytest.mark.order(5)
    def test_actions(self):
        """Test all action scenarios."""
        if not self.config.actions:
            pytest.skip("No actions configured")

        runner = ActionRunner(self)

        for name, cfg, scenarios in self.config.action_items():
            # Group action scenarios under the action name
            self._run_with_subtests(runner, scenarios, cfg, prefix=f"action_{name}")

    # -------------------------
    # List Tests
    # -------------------------

    @pytest.mark.order(6)
    def test_list(self):
        """Test list scenarios."""
        result = self.config.list_items()

        if not result:
            pytest.skip("No list scenarios configured")

        cfg, scenarios = result
        runner = ListRunner(self)
        self._run_with_subtests(runner, scenarios, cfg, prefix="list")
