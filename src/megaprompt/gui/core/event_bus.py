"""Event Bus for decoupled communication between systems."""

import logging
from collections import defaultdict
from typing import Any, Callable, Optional

from megaprompt.gui.core.events import (
    ThemeChangedEvent,
    PromptCompletedEvent,
    ProgressUpdateEvent,
    ErrorEvent,
    CommandStartedEvent,
    CommandFinishedEvent,
    ConfigChangedEvent,
    StateChangedEvent,
)

logger = logging.getLogger(__name__)

# Event type constants
EVENT_THEME_CHANGED = "theme_changed"
EVENT_PROMPT_COMPLETED = "prompt_completed"
EVENT_PROGRESS_UPDATE = "progress_update"
EVENT_ERROR = "error"
EVENT_COMMAND_STARTED = "command_started"
EVENT_COMMAND_FINISHED = "command_finished"
EVENT_CONFIG_CHANGED = "config_changed"
EVENT_STATE_CHANGED = "state_changed"


class EventBus:
    """Pub/Sub event bus for decoupled system communication."""

    _instance: Optional["EventBus"] = None

    def __new__(cls) -> "EventBus":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the event bus."""
        if self._initialized:
            return
        self._subscribers: dict[str, list[Callable[[Any], None]]] = defaultdict(list)
        self._event_log: list[tuple[str, Any]] = []
        self._max_log_size = 1000
        self._initialized = True

    def subscribe(self, event_type: str, callback: Callable[[Any], None]) -> Callable[[], None]:
        """
        Subscribe to an event type.

        Args:
            event_type: Event type constant (e.g., EVENT_THEME_CHANGED)
            callback: Callback function that receives event payload

        Returns:
            Unsubscribe function
        """
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type}")

        # Return unsubscribe function
        def unsubscribe():
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type}")

        return unsubscribe

    def publish(self, event_type: str, payload: Any, async_dispatch: bool = False) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event_type: Event type constant
            payload: Event payload (should match expected event dataclass)
            async_dispatch: If True, dispatch asynchronously (default: False)
        """
        if event_type not in self._subscribers:
            logger.debug(f"No subscribers for {event_type}")
            return

        # Log event
        self._event_log.append((event_type, payload))
        if len(self._event_log) > self._max_log_size:
            self._event_log.pop(0)

        logger.debug(f"Publishing {event_type} to {len(self._subscribers[event_type])} subscribers")

        # Dispatch to subscribers with error isolation
        for callback in list(self._subscribers[event_type]):  # Copy list to avoid modification during iteration
            try:
                if async_dispatch:
                    # For async dispatch, we'd use QTimer.singleShot or similar
                    # For now, we'll keep it synchronous but could enhance later
                    callback(payload)
                else:
                    callback(payload)
            except Exception as e:
                logger.error(f"Error in subscriber callback for {event_type}: {e}", exc_info=True)
                # Error isolation: continue to next subscriber

    def get_event_log(self, event_type: Optional[str] = None) -> list[tuple[str, Any]]:
        """
        Get event log for debugging.

        Args:
            event_type: Optional filter by event type

        Returns:
            List of (event_type, payload) tuples
        """
        if event_type:
            return [(et, payload) for et, payload in self._event_log if et == event_type]
        return list(self._event_log)

    def clear_event_log(self) -> None:
        """Clear the event log."""
        self._event_log.clear()


def get_event_bus() -> EventBus:
    """Get the singleton EventBus instance."""
    return EventBus()

