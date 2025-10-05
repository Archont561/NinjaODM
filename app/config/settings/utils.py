import inspect
import os
import sys
from typing import Any

from pydantic import SecretBytes, SecretStr
from pydantic_settings import BaseSettings

from .mixins import LoguruSettingsMixin


def to_django(settings: BaseSettings) -> None:
    """
    Export Pydantic settings to Django's global namespace.

    This function inspects the caller's frame and exports all settings
    as module-level variables that Django can use.
    """

    # Get caller's frame and its globals
    stack = inspect.stack()
    parent_frame = stack[1][0]
    parent_globals = parent_frame.f_globals  # ✅ Use f_globals, not f_locals

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

        if isinstance(val, dict):
            return {k: _get_actual_value(v) for k, v in val.items()}

        if isinstance(val, list):
            return [_get_actual_value(item) for item in val]

        if isinstance(val, (SecretStr, SecretBytes)):
            return val.get_secret_value()

        return val

    # Export all settings to caller's global namespace
    for key, value in settings.model_dump().items():
        parent_globals[key] = _get_actual_value(value)  # ✅ Use globals, not locals

    # Clean up frame reference to avoid memory leaks
    del parent_frame, stack


def is_linting_context():
    """Check if we're running in a linting/static analysis context"""
    if any(
        tool in sys.argv[0]
        for tool in ["prospector", "pylint", "mypy", "pyright", "ruff"]
    ):
        return True
    if os.getenv("SKIP_LOGURU", "").lower() in ("true", "1", "yes"):
        return True
    return False


def setup_loguru(logger, settings: LoguruSettingsMixin):
    """Configure Loguru with custom handlers"""

    # Remove default handler
    logger.remove()

    # Ensure log directory exists
    settings.LOGURU_LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Console handler
    if settings.LOGURU_ENABLE_CONSOLE:
        logger.add(
            sys.stderr,
            format=settings.LOGURU_CONSOLE_FORMAT,
            level=settings.LOGURU_CONSOLE_LEVEL,
            colorize=settings.LOGURU_COLORIZE,
            enqueue=settings.LOGURU_ENQUEUE,
            backtrace=settings.LOGURU_BACKTRACE,
            diagnose=settings.LOGURU_DIAGNOSE,
        )

    # File handler
    if settings.LOGURU_ENABLE_FILE:
        logger.add(
            str(settings.LOGURU_APP_LOG_FILE),
            format=settings.LOGURU_FILE_FORMAT,
            level=settings.LOGURU_FILE_LEVEL,
            rotation=settings.LOGURU_ROTATION_SIZE,
            retention=settings.LOGURU_RETENTION,
            compression=settings.LOGURU_COMPRESSION,
            enqueue=settings.LOGURU_ENQUEUE,
            backtrace=settings.LOGURU_BACKTRACE,
            diagnose=settings.LOGURU_DIAGNOSE,
            serialize=settings.LOGURU_SERIALIZE,
        )

    # Error file handler
    if settings.LOGURU_ENABLE_ERROR_FILE:
        logger.add(
            str(settings.LOGURU_ERROR_LOG_FILE),
            format=settings.LOGURU_FILE_FORMAT,
            level=settings.LOGURU_ERROR_FILE_LEVEL,
            rotation=settings.LOGURU_ROTATION_SIZE,
            retention=settings.LOGURU_RETENTION,
            compression=settings.LOGURU_COMPRESSION,
            enqueue=settings.LOGURU_ENQUEUE,
            backtrace=settings.LOGURU_BACKTRACE,
            diagnose=settings.LOGURU_DIAGNOSE,
        )
