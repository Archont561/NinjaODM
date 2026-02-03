from __future__ import annotations

from functools import reduce
from typing import Any, TYPE_CHECKING, TypeVar, Type

if TYPE_CHECKING:
    import pytest


T = TypeVar('T')


def merge_dicts(*dicts: dict) -> dict:
    """Merge dicts, skipping None values."""
    return reduce(
        lambda acc, d: {**acc, **{k: v for k, v in d.items() if v is not None}},
        dicts,
        {},
    )


class ResolverMixin:
    """Mixin providing fixture resolution utilities."""
    
    _request: "pytest.FixtureRequest"
    
    def fixture(self, value: Any) -> Any:
        """Resolve fixture by name or return as-is."""
        if isinstance(value, str):
            return self._request.getfixturevalue(value)
        return value
    
    def resolve_ref(
        self, 
        value: Any, 
        expected_types: tuple[Type, ...] | None = None,
        context: str = ""
    ) -> Any:
        """
        Resolve a value that might be a fixture reference.
        
        Args:
            value: The value to resolve (direct value or fixture name)
            expected_types: Tuple of types to return directly without resolution
            context: Context for better error messages
            
        Returns:
            Resolved value
            
        Raises:
            KeyError: If fixture not found
            TypeError: If resolved value doesn't match expected types
        """
        if value is None:
            return None
        
        # If it's one of the expected types, return as-is
        if expected_types and isinstance(value, expected_types):
            return value
        
        # If it's a string, resolve as fixture
        if isinstance(value, str):
            try:
                resolved = self._request.getfixturevalue(value)
            except Exception as e:
                ctx_msg = f" for {context}" if context else ""
                raise KeyError(f"Fixture '{value}' not found{ctx_msg}") from e
            
            # Validate resolved type if expected_types provided
            if expected_types and not isinstance(resolved, expected_types):
                raise TypeError(
                    f"Fixture '{value}' resolved to {type(resolved).__name__}, "
                    f"expected one of {[t.__name__ for t in expected_types]}"
                    f"{f' for {context}' if context else ''}"
                )
            return resolved
        
        # Return as-is for other types
        return value
    
    def resolve_bool(self, value: Any) -> bool | None:
        """Resolve a boolean reference."""
        return self.resolve_ref(value, (bool,), "boolean value")
    
    def resolve_int(self, value: Any) -> int | None:
        """Resolve an integer reference."""
        return self.resolve_ref(value, (int,), "integer value")
    
    def resolve_dict(self, value: Any) -> dict | None:
        """Resolve a dictionary reference."""
        return self.resolve_ref(value, (dict,), "dictionary")
    
    def resolve_list(self, value: Any) -> list | None:
        """Resolve a list reference."""
        return self.resolve_ref(value, (list,), "list")
    
    def resolve_callable(self, value: Any) -> callable | None:
        """Resolve a callable reference."""
        if value is None:
            return None
        if callable(value):
            return value
        if isinstance(value, str):
            resolved = self._request.getfixturevalue(value)
            if not callable(resolved):
                raise TypeError(f"Fixture '{value}' is not callable")
            return resolved
        raise TypeError(f"Expected callable or fixture name, got {type(value).__name__}")
    
    def resolve_status(self, value: Any, default: int | list[int] = 200) -> list[int]:
        """
        Resolve status code(s) to a list of integers.
        
        Args:
            value: Status code (int), list of codes, or fixture reference
            default: Default status code(s) if value is None
            
        Returns:
            List of acceptable status codes
        """
        if value is None:
            value = default
        
        resolved = self.resolve_ref(value, (int, list), "status code")
        
        if isinstance(resolved, int):
            return [resolved]
        return list(resolved)
    
    def call_fixture(self, value: Any, *args, **kwargs) -> Any:
        """Resolve and call if callable."""
        resolved = self.fixture(value)
        if callable(resolved):
            return resolved(*args, **kwargs) if (args or kwargs) else resolved()
        return resolved
    
    def check_assertion(self, assertion: Any, *args) -> bool:
        """
        Resolve and execute assertion.
        
        Args:
            assertion: Assertion function, fixture name, or None
            *args: Arguments to pass to assertion
            
        Returns:
            True if assertion passes or is None/returns None/True
        """
        if assertion is None:
            return True
        
        # Resolve if it's a fixture reference
        fn = self.resolve_callable(assertion)
        
        # Call the assertion
        # If it's from a fixture, pass args directly
        # If it's inline, pass self as first arg for access to resolver
        if isinstance(assertion, str):
            result = fn(*args)
        else:
            result = fn(self, *args)
        
        # None or True means success
        return result is None or result
    
    def check_denied(self, scenario: Any, obj: Any = None) -> bool:
        """
        Check if access should be denied for scenario.
        
        Args:
            scenario: Scenario object with potential access_denied attribute
            obj: Optional object to check access for
            
        Returns:
            True if access should be denied
        """
        ad = getattr(scenario, "access_denied", None)
        
        if ad is None:
            return False
        
        # Resolve boolean or callable
        if isinstance(ad, bool):
            return ad
        
        # Resolve callable (function or fixture name)
        fn = self.resolve_callable(ad) if isinstance(ad, str) else ad
        
        # Call with appropriate args
        if isinstance(ad, str):
            return fn(obj) if obj else fn()
        else:
            return fn(self, obj) if obj else fn(self)
    
    def check_status(
        self,
        response: Any,
        expected: int | list[int] | None,
        defaults: list[int],
    ) -> None:
        """
        Assert response status code matches expected.
        
        Args:
            response: HTTP response object
            expected: Expected status code(s) or None
            defaults: Default acceptable status codes
            
        Raises:
            AssertionError: If status doesn't match expected
        """
        exp = expected if expected is not None else defaults
        exp_list = [exp] if isinstance(exp, int) else list(exp)
        
        assert response.status_code in exp_list, (
            f"Expected status {exp_list}, got {response.status_code}: "
            f"{response.content.decode() if hasattr(response.content, 'decode') else response.content}"
        )
    
    def check_exists(self, model: Any, uuid: Any) -> bool:
        """
        Check if object exists in database.
        
        Args:
            model: Django model class
            uuid: Object UUID to check
            
        Returns:
            True if object exists
        """
        return model.objects.filter(uuid=uuid).exists()
    
    def get_object(self, model: Any, uuid: Any) -> Any:
        """
        Get object from database.
        
        Args:
            model: Django model class  
            uuid: Object UUID
            
        Returns:
            Model instance
            
        Raises:
            DoesNotExist: If object not found
        """
        return model.objects.get(uuid=uuid)
