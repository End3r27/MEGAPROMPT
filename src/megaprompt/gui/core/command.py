"""Command Orchestration system for translating UI actions into executable commands."""

from __future__ import annotations

import logging
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from megaprompt.gui.core.event_bus import EventBus, EVENT_COMMAND_STARTED, EVENT_COMMAND_FINISHED
from megaprompt.gui.core.interface import MegaPromptCoreInterface, Result

logger = logging.getLogger(__name__)


class CommandStatus(str, Enum):
    """Command status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CommandResult:
    """Result of command execution."""

    success: bool
    result: Any = None
    error: Optional[str] = None


class Command(ABC):
    """Abstract base class for commands."""

    def __init__(self, command_type: str, description: str):
        self.command_id = str(uuid.uuid4())
        self.command_type = command_type
        self.description = description
        self.status = CommandStatus.PENDING
        self.result: Optional[CommandResult] = None
        self._cancelled = False

    @abstractmethod
    def execute(self) -> CommandResult:
        """
        Execute the command.

        Returns:
            CommandResult with success status and result/error
        """
        pass

    def can_undo(self) -> bool:
        """Check if command can be undone."""
        return False  # Most commands cannot be undone (network operations)

    def undo(self) -> CommandResult:
        """Undo the command (if supported)."""
        return CommandResult(success=False, error="Undo not supported for this command")

    def cancel(self) -> None:
        """Cancel the command execution."""
        self._cancelled = True
        self.status = CommandStatus.CANCELLED

    def is_cancelled(self) -> bool:
        """Check if command is cancelled."""
        return self._cancelled


class GeneratePromptCommand(Command):
    """Command for generating a mega-prompt."""

    def __init__(self, core_interface: MegaPromptCoreInterface, user_prompt: str, config: dict[str, Any]):
        super().__init__("generate_prompt", f"Generate prompt: {user_prompt[:50]}...")
        self.core_interface = core_interface
        self.user_prompt = user_prompt
        self.config = config

    def execute(self) -> CommandResult:
        """Execute prompt generation."""
        if self.is_cancelled():
            return CommandResult(success=False, error="Command cancelled")

        try:
            result = self.core_interface.generate_prompt(self.user_prompt, self.config)
            if result.is_ok():
                return CommandResult(success=True, result=result.value)
            else:
                error_msg = result.error.message if result.error else "Unknown error"
                return CommandResult(success=False, error=error_msg)
        except Exception as e:
            logger.error(f"Error executing GeneratePromptCommand: {e}", exc_info=True)
            return CommandResult(success=False, error=str(e))


class AnalyzeCodebaseCommand(Command):
    """Command for analyzing a codebase."""

    def __init__(self, core_interface: MegaPromptCoreInterface, codebase_path: str, config: dict[str, Any], mode: str = "full"):
        super().__init__("analyze_codebase", f"Analyze codebase: {codebase_path}")
        self.core_interface = core_interface
        self.codebase_path = codebase_path
        self.config = config
        self.mode = mode

    def execute(self) -> CommandResult:
        """Execute codebase analysis."""
        if self.is_cancelled():
            return CommandResult(success=False, error="Command cancelled")

        try:
            result = self.core_interface.analyze_codebase(self.codebase_path, self.config, self.mode)
            if result.is_ok():
                return CommandResult(success=True, result=result.value)
            else:
                error_msg = result.error.message if result.error else "Unknown error"
                return CommandResult(success=False, error=error_msg)
        except Exception as e:
            logger.error(f"Error executing AnalyzeCodebaseCommand: {e}", exc_info=True)
            return CommandResult(success=False, error=str(e))


class CommandWorker(QThread):
    """QThread worker for executing commands in background."""

    finished = pyqtSignal(object, object)  # command, result

    def __init__(self, command: Command):
        super().__init__()
        self.command = command

    def run(self) -> None:
        """Execute the command."""
        self.command.status = CommandStatus.RUNNING
        result = self.command.execute()
        self.command.result = result
        if self.command.is_cancelled():
            self.command.status = CommandStatus.CANCELLED
        else:
            self.command.status = CommandStatus.COMPLETED if result.success else CommandStatus.FAILED
        self.finished.emit(self.command, result)


class CommandManager(QObject):
    """Manages command execution and history."""

    def __init__(self, core_interface: MegaPromptCoreInterface, event_bus: EventBus):
        super().__init__()
        self.core_interface = core_interface
        self.event_bus = event_bus
        self._command_history: list[Command] = []
        self._active_commands: dict[str, CommandWorker] = {}
        self._max_history_size = 100

    def execute(self, command: Command, background: bool = True) -> None:
        """
        Execute a command.

        Args:
            command: Command to execute
            background: If True, execute in background thread (default: True)
        """
        # Publish command started event
        from megaprompt.gui.core.events import CommandStartedEvent

        self.event_bus.publish(
            EVENT_COMMAND_STARTED,
            CommandStartedEvent(
                command_id=command.command_id,
                command_type=command.command_type,
                description=command.description,
            ),
        )

        if background:
            # Execute in background thread
            worker = CommandWorker(command)
            worker.finished.connect(lambda cmd, result: self._on_command_finished(cmd, result))
            self._active_commands[command.command_id] = worker
            worker.start()
        else:
            # Execute synchronously (for testing or simple commands)
            command.status = CommandStatus.RUNNING
            result = command.execute()
            command.result = result
            command.status = CommandStatus.COMPLETED if result.success else CommandStatus.FAILED
            self._on_command_finished(command, result)

    def _on_command_finished(self, command: Command, result: CommandResult) -> None:
        """Handle command completion."""
        # Remove from active commands
        self._active_commands.pop(command.command_id, None)

        # Add to history
        self._command_history.append(command)
        if len(self._command_history) > self._max_history_size:
            self._command_history.pop(0)

        # Publish command finished event
        from megaprompt.gui.core.events import CommandFinishedEvent

        self.event_bus.publish(
            EVENT_COMMAND_FINISHED,
            CommandFinishedEvent(
                command_id=command.command_id,
                command_type=command.command_type,
                success=result.success,
                result=result.result if result.success else None,
                error=result.error,
            ),
        )

    def cancel_command(self, command_id: str) -> bool:
        """
        Cancel a running command.

        Args:
            command_id: Command ID to cancel

        Returns:
            True if command was cancelled, False if not found or already finished
        """
        worker = self._active_commands.get(command_id)
        if worker:
            command = worker.command
            command.cancel()
            worker.terminate()  # Force terminate the thread
            worker.wait(1000)  # Wait up to 1 second
            self._active_commands.pop(command_id, None)
            return True
        return False

    def get_command_history(self) -> list[Command]:
        """Get command history."""
        return list(self._command_history)

    def clear_history(self) -> None:
        """Clear command history."""
        self._command_history.clear()

