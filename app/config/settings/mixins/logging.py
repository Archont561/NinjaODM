from pathlib import Path
from pydantic import Field, computed_field
from .base import BaseSettingsMixin
from enum import StrEnum, auto


class LogLevels(StrEnum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        """Generate uppercase string values for enum members"""
        return name.upper()

    TRACE = auto()
    DEBUG = auto()
    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


class LoguruSettingsMixin(BaseSettingsMixin):
    # Log levels
    LOGURU_CONSOLE_LEVEL: LogLevels = Field(default=LogLevels.INFO)
    LOGURU_FILE_LEVEL: LogLevels = Field(default=LogLevels.DEBUG)
    LOGURU_ERROR_FILE_LEVEL: LogLevels = Field(default=LogLevels.ERROR)

    # Format
    LOGURU_USE_JSON_FORMAT: bool = Field(default=False)
    LOGURU_COLORIZE: bool = Field(default=True)

    # Console format
    LOGURU_CONSOLE_FORMAT: str = Field(
        default=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # File format
    LOGURU_FILE_FORMAT: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    # Rotation
    LOGURU_ROTATION_SIZE: str = Field(default="100 MB")
    LOGURU_ROTATION_TIME: str = Field(default="00:00")  # Daily at midnight
    LOGURU_RETENTION: str = Field(default="30 days")
    LOGURU_COMPRESSION: str = Field(default="zip")

    # Performance
    LOGURU_ENQUEUE: bool = Field(default=True)
    LOGURU_BACKTRACE: bool = Field(default=True)
    LOGURU_DIAGNOSE: bool = Field(default=True)

    # Handlers
    LOGURU_ENABLE_CONSOLE: bool = Field(default=True)
    LOGURU_ENABLE_FILE: bool = Field(default=True)
    LOGURU_ENABLE_ERROR_FILE: bool = Field(default=True)

    # Django integration
    LOGURU_INTERCEPT_DJANGO: bool = Field(default=True)

    # Serialize (JSON output)
    LOGURU_SERIALIZE: bool = Field(default=False)

    @computed_field
    @property
    def LOGURU_LOGS_DIR(self) -> Path:
        return self.APP_DIR / "logs"

    @computed_field
    @property
    def LOGURU_APP_LOG_FILE(self) -> Path:
        return self.LOGURU_LOGS_DIR / "app.log"

    @computed_field
    @property
    def LOGURU_ERROR_LOG_FILE(self) -> Path:
        return self.LOGURU_LOGS_DIR / "error.log"

    @computed_field
    @property
    def LOGURU_JSON_LOG_FILE(self) -> Path:
        return self.LOGURU_LOGS_DIR / "app.json.log"
