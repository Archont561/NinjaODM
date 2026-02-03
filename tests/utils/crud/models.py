from __future__ import annotations

from typing import Any, Callable, ClassVar, Optional, Union
from pydantic import BaseModel, Field


# -------------------------
# Type Aliases (Fixture Compatible)
# -------------------------

# Generic alias for a value that can be T or a fixture name (str)
Fixture = Union[str, Any]

# Specific aliases for clearer intent
Ref = Union[Any, str]                  # General reference or fixture
FnRef = Union[Callable, str]           # Function, Lambda, or fixture name
DictRef = Union[dict[str, Any], str]   # Dictionary or fixture name
ListRef = Union[list[Any], str]        # List or fixture name
IntRef = Union[int, str]               # Integer or fixture name
BoolRef = Union[bool, str]             # Boolean or fixture name
StatusRef = Union[int, list[int], str] # Status code(s) or fixture name


# -------------------------
# Base Model
# -------------------------

class Model(BaseModel):
    """Base model with common config."""
    
    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True,
        "extra": "forbid",
    }


# -------------------------
# Field Mixins
# -------------------------

class NamedMixin(Model):
    name: Optional[str] = None


class EndpointMixin(Model):
    endpoint: Optional[str] = None


class ModelRefMixin(Model):
    model: Optional[Ref] = None


class ClientMixin(Model):
    client: Optional[Ref] = None


class FactoryMixin(Model):
    factory: Optional[FnRef] = None


class AssertionMixin(Model):
    assertion: Optional[FnRef] = Field(None, alias="assert")
    expected_status: Optional[StatusRef] = None
    access_denied: Optional[BoolRef] = None


# -------------------------
# HTTP Mixin
# -------------------------

class HttpMixin(Model):
    """Mixin for HTTP request configuration."""
    url: Optional[FnRef] = None
    method: Optional[str] = None
    payload: Optional[Union[dict, list, Callable, str]] = None 
    files: Optional[FnRef] = None
    headers: Optional[DictRef] = None
    query: Optional[DictRef] = None


# -------------------------
# Queries Mixin
# -------------------------

class QueriesMixin(Model):
    # Can be a list of dicts, or a fixture name returning that list
    queries: Optional[ListRef] = None


# -------------------------
# Scenario Config Mixin
# -------------------------

class ScenarioConfigMixin(Model):
    """Mixin for configs with scenarios."""
    
    scenarios: list[dict] = Field(default_factory=list)
    
    _scenario_class: ClassVar[type]
    _inherit_fields: ClassVar[set[str]] = set()
    
    def get_scenarios(self, merge_fn, parent_defaults: dict) -> list:
        """Build scenarios: parent defaults → config → scenario."""
        config_values = self.model_dump(include=self._inherit_fields, exclude_none=True)
        base = merge_fn(parent_defaults, config_values)
        return [
            self._scenario_class(**merge_fn(base, s))
            for s in self.scenarios
        ]


# -------------------------
# Base Scenario
# -------------------------

class BaseScenario(
    NamedMixin,
    EndpointMixin,
    ModelRefMixin,
    ClientMixin,
    FactoryMixin,
    AssertionMixin,
):
    """Base for all scenarios."""
    pass


# -------------------------
# Base Operation Config
# -------------------------

class BaseOperationConfig(
    NamedMixin,
    EndpointMixin,
    ModelRefMixin,
    ClientMixin,
    FactoryMixin,
    AssertionMixin,
    ScenarioConfigMixin,
):
    """Base for operation configs."""
    pass


# -------------------------
# CRUD
# -------------------------

class CRUDScenario(BaseScenario, HttpMixin):
    """CRUD scenario with HTTP capabilities."""
    pass


class CRUDConfig(BaseOperationConfig, HttpMixin):
    """CRUD operation config."""
    
    _scenario_class: ClassVar[type] = CRUDScenario
    _inherit_fields: ClassVar[set[str]] = {
        "endpoint", "model", "client", "factory",
        "assertion", "expected_status", "access_denied",
        "url", "method", "payload", "files", "headers", "query",
    }


# -------------------------
# Action
# -------------------------

class ActionScenario(BaseScenario, HttpMixin):
    """Action scenario with HTTP capabilities."""
    pass


class ActionConfig(BaseOperationConfig, HttpMixin):
    """Action config."""
    
    method: str = "post"  # Default for actions
    
    _scenario_class: ClassVar[type] = ActionScenario
    _inherit_fields: ClassVar[set[str]] = {
        "endpoint", "model", "client", "factory",
        "assertion", "expected_status", "access_denied",
        "url", "method", "payload", "files", "headers", "query",
    }


# -------------------------
# List
# -------------------------

class ListQuery(Model):
    """Single list query."""
    
    params: DictRef = Field(default_factory=dict)
    assertion: Optional[FnRef] = Field(None, alias="assert")
    expected_status: StatusRef = 200
    expected_count: Optional[IntRef] = None
    headers: Optional[DictRef] = None


class ListScenario(BaseScenario, HttpMixin, QueriesMixin):
    """List scenario."""
    pass


class ListConfig(BaseOperationConfig, HttpMixin, QueriesMixin):
    """List config."""
    
    method: str = "get"  # Default for list
    
    _scenario_class: ClassVar[type] = ListScenario
    _inherit_fields: ClassVar[set[str]] = {
        "endpoint", "model", "client", "factory",
        "assertion", "expected_status", "access_denied",
        "url", "method", "headers", "query", "queries",
    }
