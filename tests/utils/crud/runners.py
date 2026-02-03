from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar, List
from urllib.parse import urlencode, urljoin

from .models import (
    CRUDScenario,
    CRUDConfig,
    ActionScenario,
    ActionConfig,
    ListScenario,
    ListConfig,
    ListQuery,
)
from .utils import ResolverMixin


S = TypeVar("S")
C = TypeVar("C")


class BaseRunner(ABC, Generic[S, C]):
    """Base runner for scenarios."""

    def __init__(self, resolver: ResolverMixin):
        self.r = resolver

    @abstractmethod
    def run(self, scenario: S, index: int, config: C | None = None) -> None:
        pass

    def run_all(self, scenarios: list[S], config: C | None = None) -> None:
        for i, scenario in enumerate(scenarios):
            self.run(scenario, i, config)

    def sid(self, scenario: S, index: int, prefix: str = "") -> str:
        """Get scenario ID for error messages."""
        name = getattr(scenario, "name", None) or f"scenario_{index}"
        return f"{prefix}_{name}" if prefix else name

    def resolve_http_kwargs(self, scenario, config=None) -> dict:
        """Build HTTP request kwargs from scenario and config."""
        kwargs = {}

        # --- Payload ---
        payload_source = scenario.payload or (config.payload if config else None)
        if payload_source is not None:
            if callable(payload_source):
                kwargs["json"] = payload_source(self.r)
            else:
                # Handles dict, list, or fixture reference
                kwargs["json"] = self.r.resolve_ref(
                    payload_source, (dict, list), "payload"
                )

        # --- Files ---
        files_source = scenario.files or (config.files if config else None)
        if files_source:
            # Files are typically always from fixtures
            kwargs["FILES"] = self.r.fixture(files_source)

        # --- Headers ---
        headers_source = scenario.headers or (config.headers if config else None)
        if headers_source:
            kwargs["headers"] = self.r.resolve_dict(headers_source)

        # --- Query Params ---
        query_source = scenario.query or (config.query if config else None)
        if query_source:
            kwargs["query"] = self.r.resolve_dict(query_source)

        return kwargs

    def resolve_url(self, scenario, config, obj=None) -> str:
        """Resolve URL from scenario or config."""
        url_source = scenario.url or (config.url if config else None)

        if url_source:
            if callable(url_source):
                return url_source(self.r, obj) if obj else url_source(self.r)

            # Try to resolve as fixture first
            resolved_url = self.r.resolve_ref(url_source, (str,), "url")

            # Format if object provided
            try:
                return resolved_url.format(obj=obj) if obj else resolved_url
            except (KeyError, AttributeError):
                return resolved_url

        # Fallback to endpoint + obj.uuid
        endpoint = scenario.endpoint or (config.endpoint if config else "/")
        if obj:
            if not endpoint.endswith("/"):
                endpoint += "/"
            return urljoin(endpoint, str(obj.uuid))
        return endpoint

    def resolve_method(self, scenario, config, default: str = "get") -> str:
        """Resolve HTTP method from scenario or config."""
        return scenario.method or (config.method if config else None) or default


class CRUDRunner(BaseRunner[CRUDScenario, CRUDConfig]):
    """CRUD operations runner."""

    def __init__(self, resolver: ResolverMixin, operation: str):
        super().__init__(resolver)
        self.operation = operation

    def run(
        self, scenario: CRUDScenario, index: int, config: CRUDConfig | None = None
    ) -> None:
        handler = getattr(self, f"_do_{self.operation}", None)
        if not handler:
            raise ValueError(f"Unknown CRUD operation: {self.operation}")
        handler(scenario, index, config)

    # --- Shared Helpers ---

    def _resolve_and_request(
        self,
        s: CRUDScenario,
        config: CRUDConfig | None,
        obj: Any = None,
        default_method: str = "get",
        default_status: List[int] | None = None,  # <--- Added parameter
        denied_codes: List[int] | None = None,
    ) -> tuple[Any, dict, bool]:
        """
        Handles URL resolution, making the request, and checking access/status.
        Returns: (Response, Kwargs, AccessDeniedBoolean)
        """
        client = self.r.fixture(s.client)
        url = self.resolve_url(s, config, obj)
        method = self.resolve_method(s, config, default_method)
        kwargs = self.resolve_http_kwargs(s, config)

        # Resolve expected status with the provided defaults
        if default_status is None:
            default_status = [200]
        expected_status = self.r.resolve_status(s.expected_status, default_status)

        if denied_codes is None:
            denied_codes = [401, 403, 404]

        # Make request
        resp = getattr(client, method)(url, **kwargs)

        # Check access
        is_denied = self.r.check_denied(s, obj) if obj else self.r.check_denied(s)

        if is_denied:
            self.r.check_status(resp, expected_status, denied_codes)
            return resp, kwargs, True

        # Check success status (pass all potential success codes to allow flexibility)
        self.r.check_status(resp, expected_status, [200, 201, 204])
        return resp, kwargs, False

    def _finalize_assertion(
        self, s: CRUDScenario, sid: str, obj: Any, comparison_data: Any
    ) -> None:
        if s.assertion:
            assert self.r.check_assertion(s.assertion, obj, comparison_data), (
                f"[{sid}] Assertion failed"
            )

    # --- Operation Handlers ---

    def _do_create(
        self, s: CRUDScenario, i: int, config: CRUDConfig | None = None
    ) -> None:
        sid = self.sid(s, i, "create")

        resp, kwargs, denied = self._resolve_and_request(
            s,
            config,
            default_method="post",
            default_status=[200, 201],
            denied_codes=[401, 403, 404, 422],
        )
        if denied:
            return

        data = resp.json()
        obj_id = data.get("uuid") or data.get("id")
        assert obj_id, f"[{sid}] No uuid/id in response: {data}"

        obj = self.r.get_object(s.model, obj_id)
        self._finalize_assertion(s, sid, obj, kwargs.get("json", {}))

    def _do_get(
        self, s: CRUDScenario, i: int, config: CRUDConfig | None = None
    ) -> None:
        sid = self.sid(s, i, "get")
        obj = self.r.call_fixture(s.factory)

        resp, _, denied = self._resolve_and_request(
            s, config, obj=obj, default_method="get", default_status=[200]
        )
        if denied:
            return

        self._finalize_assertion(s, sid, obj, resp)

    def _do_update(
        self, s: CRUDScenario, i: int, config: CRUDConfig | None = None
    ) -> None:
        sid = self.sid(s, i, "update")
        obj = self.r.call_fixture(s.factory)

        resp, kwargs, denied = self._resolve_and_request(
            s, config, obj=obj, default_method="patch", default_status=[200]
        )
        if denied:
            return

        obj.refresh_from_db()
        self._finalize_assertion(s, sid, obj, kwargs.get("json", {}))

    def _do_delete(
        self, s: CRUDScenario, i: int, config: CRUDConfig | None = None
    ) -> None:
        sid = self.sid(s, i, "delete")
        obj = self.r.call_fixture(s.factory)
        obj_uuid = obj.uuid

        resp, _, denied = self._resolve_and_request(
            s, config, obj=obj, default_method="delete", default_status=[200, 204]
        )

        if denied:
            assert self.r.check_exists(s.model, obj_uuid), (
                f"[{sid}] Object deleted but access should be denied"
            )
            return

        assert not self.r.check_exists(s.model, obj_uuid), f"[{sid}] Object not deleted"
        self._finalize_assertion(s, sid, obj, resp)


class ActionRunner(BaseRunner[ActionScenario, ActionConfig]):
    """Action operations runner."""

    def run(
        self, scenario: ActionScenario, index: int, config: ActionConfig | None = None
    ) -> None:
        if not config:
            raise ValueError("ActionRunner requires config")

        sid = self.sid(scenario, index, "action")
        client = self.r.fixture(scenario.client)

        # Factory is optional for Actions
        obj = None
        if scenario.factory:
            obj = self.r.call_fixture(scenario.factory)

        url = self.resolve_url(scenario, config, obj)
        method = self.resolve_method(scenario, config, "post")
        kwargs = self.resolve_http_kwargs(scenario, config)

        expected_status = self.r.resolve_status(scenario.expected_status, [200])

        # Make request
        resp = getattr(client, method)(url, **kwargs)

        # Check access
        if self.r.check_denied(scenario, obj):
            self.r.check_status(resp, expected_status, [401, 403, 404])
            return

        # Run assertion or check status
        if scenario.assertion:
            assert self.r.check_assertion(scenario.assertion, obj, resp), (
                f"[{sid}] Assertion failed"
            )
        else:
            self.r.check_status(resp, expected_status, [200])


class ListRunner(BaseRunner[ListScenario, ListConfig]):
    """List operations runner."""

    def run(
        self, scenario: ListScenario, index: int, config: ListConfig | None = None
    ) -> None:
        if not config:
            raise ValueError("ListRunner requires config")

        sid = self.sid(scenario, index, "list")
        client = self.r.fixture(scenario.client)

        url = self.resolve_url(scenario, config)
        method = self.resolve_method(scenario, config, "get")

        # Setup data if factory provided
        if scenario.factory:
            self.r.call_fixture(scenario.factory)

        # Resolve queries
        queries = self._resolve_queries(scenario.queries or config.queries)

        # Base HTTP kwargs (headers, etc.)
        base_kwargs = self.resolve_http_kwargs(scenario, config)

        # Run each query
        for qi, query in enumerate(queries):
            self._run_query(sid, qi, client, method, url, query, base_kwargs)

        # Run scenario-level assertion if provided
        if scenario.assertion:
            assert self.r.check_assertion(scenario.assertion), (
                f"[{sid}] Scenario assertion failed"
            )

    def _resolve_queries(self, queries: Any) -> list[ListQuery]:
        """Resolve queries configuration to ListQuery objects."""
        if queries is None:
            return []

        # Resolve list of query dicts
        data = self.r.resolve_list(queries)

        return [ListQuery(**q) for q in data] if data else []

    def _run_query(
        self,
        sid: str,
        qi: int,
        client: Any,
        method: str,
        url: str,
        query: ListQuery,
        base_kwargs: dict,
    ) -> None:
        """Execute a single list query."""
        qid = f"{sid}_q{qi}"

        # Resolve query parameters
        params = self.r.resolve_dict(query.params)

        # Build full URL with query params
        if params:
            query_string = urlencode(params)
            full_url = f"{url}?{query_string}"
        else:
            full_url = url

        # Merge headers
        kwargs = {**base_kwargs}
        if query.headers:
            q_headers = self.r.resolve_dict(query.headers)
            if q_headers:
                kwargs["headers"] = {**kwargs.get("headers", {}), **q_headers}

        # Make request
        resp = getattr(client, method)(full_url, **kwargs)

        # Check status
        expected_status = self.r.resolve_status(query.expected_status, 200)

        assert resp.status_code in expected_status, (
            f"[{qid}] Status {resp.status_code} not in {expected_status}, url={full_url}"
        )

        if resp.status_code != 200:
            return

        # Check count if specified
        if query.expected_count is not None:
            expected_count = self.r.resolve_int(query.expected_count)

            data = resp.json()

            # Extract items from paginated or direct response
            if isinstance(data, dict):
                items = data.get("results", data.get("items", data.get("data", data)))
            else:
                items = data

            if isinstance(items, list):
                assert len(items) == expected_count, (
                    f"[{qid}] Count {len(items)} != {expected_count}, url={full_url}"
                )
            elif expected_count == 0:
                # Allow empty dict/None for zero count
                pass
            else:
                raise AssertionError(
                    f"[{qid}] Cannot verify count for non-list response: {type(items).__name__}"
                )

        # Run query-level assertion if provided
        if query.assertion:
            assert self.r.check_assertion(query.assertion, resp), (
                f"[{qid}] Query assertion failed"
            )
