"""Event type definitions for the Event Bus."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ThemeChangedEvent:
    """Event emitted when theme changes."""
    theme: str
    colors: dict[str, str]


@dataclass
class PromptCompletedEvent:
    """Event emitted when prompt generation completes."""
    result: str
    intermediate_outputs: dict[str, Any]
    success: bool


@dataclass
class ProgressUpdateEvent:
    """Event emitted for progress updates."""
    stage: str
    message: str
    progress: float  # 0.0 to 1.0
    current: Optional[int] = None
    total: Optional[int] = None


@dataclass
class ErrorEvent:
    """Event emitted when an error occurs."""
    error_type: str
    message: str
    details: Optional[dict[str, Any]] = None


@dataclass
class CommandStartedEvent:
    """Event emitted when a command starts."""
    command_id: str
    command_type: str
    description: str


@dataclass
class CommandFinishedEvent:
    """Event emitted when a command finishes."""
    command_id: str
    command_type: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class ConfigChangedEvent:
    """Event emitted when configuration changes."""
    config: dict[str, Any]


@dataclass
class StateChangedEvent:
    """Event emitted when application state changes."""
    key: str
    value: Any

