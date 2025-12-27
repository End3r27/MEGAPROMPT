"""Core systems for the GUI application."""

from megaprompt.gui.core.event_bus import EventBus
from megaprompt.gui.core.state import StateManager
from megaprompt.gui.core.interface import MegaPromptCoreInterface
from megaprompt.gui.core.command import Command, CommandManager

__all__ = [
    "EventBus",
    "StateManager",
    "MegaPromptCoreInterface",
    "Command",
    "CommandManager",
]

