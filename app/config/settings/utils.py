import inspect
from typing import Any, Dict

from pydantic import SecretBytes, SecretStr
from pydantic_settings import BaseSettings


def to_django(settings: BaseSettings) -> None:
    """
    Export Pydantic settings to Django's global namespace.

    This function inspects the caller's frame and exports all settings
    as module-level variables that Django can use.
    """

    # Get caller's frame
    stack = inspect.stack()
    parent_frame = stack[1][0]

    def _get_actual_value(val: Any) -> Any:
        """
        Recursively extract actual values from Pydantic models.

        Handles:
        - Nested BaseSettings (converts to dict)
        - Dicts (recursively processes values)
        - Lists (recursively processes items)
        - SecretStr/SecretBytes (extracts secret value)
        - Everything else (returns as-is)
        """
        if isinstance(val, BaseSettings):
            # Convert nested settings to dict and process
            return _get_actual_value(val.model_dump())
        elif isinstance(val, dict):
            return {k: _get_actual_value(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [_get_actual_value(item) for item in val]
        elif isinstance(val, (SecretStr, SecretBytes)):
            return val.get_secret_value()
        else:
            return val

    # Export all settings to caller's namespace
    for key, value in settings.model_dump().items():
        parent_frame.f_locals[key] = _get_actual_value(value)
