# app/config/loguru_setup.py
"""Setup Loguru for Django."""

from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from app.config.settings.main import PydanticDjangoSettings

# Initialization flag
_loguru_initialized = False


def setup_loguru(settings: PydanticDjangoSettings | None = None) -> None:
    """
    Configure Loguru based on settings.

    Args:
        settings: Django settings instance. If None, will load from loader.
    """
    global _loguru_initialized

    # Prevent double initialization
    if _loguru_initialized:
        return

    # Skip during certain commands
    skip_commands = ['makemigrations', 'migrate', 'compilemessages', 'collectstatic']
    if any(cmd in sys.argv for cmd in skip_commands):
        _loguru_initialized = True
        return

    # Skip during auto-reloader parent process
    if os.environ.get('RUN_MAIN') != 'true' and 'runserver' in sys.argv:
        return

    # Get settings
    if settings is None:
        try:
            from app.config.settings.loader import get_pydantic_settings
            settings = get_pydantic_settings()
        except Exception:
            # Settings not ready yet
            return

    # Ensure logs directory exists
    try:
        settings.LOGURU_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning: Failed to create logs directory: {e}", file=sys.stderr)

    # Remove default handler
    logger.remove()

    # Console handler
    if settings.LOGURU_ENABLE_CONSOLE:
        logger.add(
            sys.stdout,
            level=settings.LOGURU_CONSOLE_LEVEL.upper(),
            format=settings.LOGURU_CONSOLE_FORMAT,
            colorize=settings.LOGURU_COLORIZE and not settings.LOGURU_USE_JSON_FORMAT,
            serialize=settings.LOGURU_USE_JSON_FORMAT,
            backtrace=settings.LOGURU_BACKTRACE,
            diagnose=settings.LOGURU_DIAGNOSE,
            enqueue=False,  # Console should not be async
        )

    # File handler
    if settings.LOGURU_ENABLE_FILE:
        file_path = settings.LOGURU_JSON_LOG_FILE if settings.LOGURU_USE_JSON_FORMAT else settings.LOGURU_APP_LOG_FILE
        logger.add(
            str(file_path),
            level=settings.LOGURU_FILE_LEVEL.upper(),
            format=settings.LOGURU_FILE_FORMAT if not settings.LOGURU_USE_JSON_FORMAT else None,
            rotation=settings.LOGURU_ROTATION_SIZE,
            retention=settings.LOGURU_RETENTION,
            compression=settings.LOGURU_COMPRESSION,
            serialize=settings.LOGURU_USE_JSON_FORMAT,
            backtrace=settings.LOGURU_BACKTRACE,
            diagnose=settings.LOGURU_DIAGNOSE,
            enqueue=settings.LOGURU_ENQUEUE,
        )

    # Error file handler
    if settings.LOGURU_ENABLE_ERROR_FILE:
        logger.add(
            str(settings.LOGURU_ERROR_LOG_FILE),
            level=settings.LOGURU_ERROR_FILE_LEVEL.upper(),
            format=settings.LOGURU_FILE_FORMAT,
            rotation=settings.LOGURU_ROTATION_SIZE,
            retention=settings.LOGURU_RETENTION,
            compression=settings.LOGURU_COMPRESSION,
            backtrace=True,
            diagnose=True,
            enqueue=settings.LOGURU_ENQUEUE,
        )

    # Intercept Django logging
    if settings.LOGURU_INTERCEPT_DJANGO:
        _setup_django_intercept()

    # Mark as initialized
    _loguru_initialized = True

    logger.info("🚀 Loguru initialized successfully")


def _setup_django_intercept() -> None:
    """Intercept Django's standard logging and route to Loguru."""

    class InterceptHandler(logging.Handler):
        """Handler that intercepts standard logging and routes to Loguru."""

        def emit(self, record: logging.LogRecord) -> None:
            """Emit a log record to Loguru."""
            # Get corresponding Loguru level
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # Find caller from where originated the logged message
            frame, depth = logging.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # Replace handlers for Django's root logger
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(0)

    # Replace handlers for specific Django loggers
    for logger_name in ['django', 'django.request', 'django.server', 'django.db.backends']:
        django_logger = logging.getLogger(logger_name)
        django_logger.handlers = []
        django_logger.propagate = True


def reset_loguru() -> None:
    """Reset Loguru initialization (for testing)."""
    global _loguru_initialized
    _loguru_initialized = False
    logger.remove()