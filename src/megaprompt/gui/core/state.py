"""State Persistence system for saving and loading application state."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Current state schema version
STATE_VERSION = 1

# Default state schema
DEFAULT_STATE = {
    "version": STATE_VERSION,
    "window": {
        "geometry": None,  # [x, y, width, height]
        "maximized": False,
    },
    "settings": {
        "provider": "auto",
        "model": None,
        "theme": "dark",
    },
    "recent_prompts": [],
    "recent_files": [],
}


class StateManager:
    """Manages application state persistence."""

    def __init__(self, state_file: Optional[Path] = None):
        """
        Initialize state manager.

        Args:
            state_file: Path to state file (default: ~/.megaprompt/gui_state.json)
        """
        if state_file is None:
            state_file = Path.home() / ".megaprompt" / "gui_state.json"
        self.state_file = state_file
        self.state_dir = state_file.parent
        self._state: dict[str, Any] = {}
        self._save_enabled = True
        self._load_state()

    def _load_state(self) -> None:
        """Load state from file, falling back to defaults if needed."""
        try:
            if self.state_file.exists():
                content = self.state_file.read_text(encoding="utf-8")
                self._state = json.loads(content)

                # Validate and migrate state version
                version = self._state.get("version", 0)
                if version < STATE_VERSION:
                    logger.info(f"Migrating state from version {version} to {STATE_VERSION}")
                    self._migrate_state(version)
                elif version > STATE_VERSION:
                    logger.warning(f"State version {version} is newer than current {STATE_VERSION}, resetting")
                    self._state = self._get_default_state()

                # Merge with defaults to ensure all keys exist
                default = self._get_default_state()
                for key, default_value in default.items():
                    if key not in self._state:
                        self._state[key] = default_value
            else:
                # No state file, use defaults
                self._state = self._get_default_state()
        except json.JSONDecodeError as e:
            logger.warning(f"State file corrupted: {e}, attempting to load backup")
            # Try backup
            backup_file = self.state_file.with_suffix(".json.bak")
            if backup_file.exists():
                try:
                    content = backup_file.read_text(encoding="utf-8")
                    self._state = json.loads(content)
                    logger.info("Loaded state from backup file")
                except Exception as backup_error:
                    logger.error(f"Backup file also corrupted: {backup_error}, resetting to defaults")
                    self._state = self._get_default_state()
            else:
                logger.warning("No backup file found, resetting to defaults")
                self._state = self._get_default_state()
        except PermissionError as e:
            logger.error(f"Permission denied loading state: {e}")
            self._state = self._get_default_state()
            self._save_enabled = False
        except IOError as e:
            logger.error(f"IO error loading state: {e}")
            self._state = self._get_default_state()
            if "No space left" in str(e) or "disk full" in str(e).lower():
                self._save_enabled = False

    def _get_default_state(self) -> dict[str, Any]:
        """Get default state (deep copy)."""
        return json.loads(json.dumps(DEFAULT_STATE))

    def _migrate_state(self, from_version: int) -> None:
        """Migrate state from older version to current version."""
        # For now, just reset to defaults if version mismatch
        # In the future, we could implement proper migration logic here
        if from_version < STATE_VERSION:
            logger.info("Resetting state to current version defaults")
            self._state = self._get_default_state()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a state value using dot notation (e.g., 'window.geometry').

        Args:
            key: State key, supports dot notation for nested access
            default: Default value if key not found

        Returns:
            State value or default
        """
        keys = key.split(".")
        value = self._state
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """
        Set a state value using dot notation (e.g., 'window.geometry').

        Args:
            key: State key, supports dot notation for nested access
            value: Value to set
        """
        keys = key.split(".")
        target = self._state
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    def save(self) -> bool:
        """
        Save state to file with atomic write.

        Returns:
            True if successful, False otherwise
        """
        if not self._save_enabled:
            logger.debug("Save disabled (permission or disk space issue)")
            return False

        try:
            # Ensure directory exists
            self.state_dir.mkdir(parents=True, exist_ok=True)

            # Update version
            self._state["version"] = STATE_VERSION

            # Create backup
            if self.state_file.exists():
                backup_file = self.state_file.with_suffix(".json.bak")
                try:
                    backup_file.write_bytes(self.state_file.read_bytes())
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")

            # Atomic write: write to temp file then rename
            temp_file = self.state_file.with_suffix(".json.tmp")
            content = json.dumps(self._state, indent=2)
            temp_file.write_text(content, encoding="utf-8")
            temp_file.replace(self.state_file)

            logger.debug(f"State saved to {self.state_file}")
            return True
        except PermissionError as e:
            logger.error(f"Permission denied saving state: {e}")
            self._save_enabled = False
            return False
        except IOError as e:
            logger.error(f"IO error saving state: {e}")
            if "No space left" in str(e) or "disk full" in str(e).lower():
                self._save_enabled = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving state: {e}", exc_info=True)
            return False

    def get_all(self) -> dict[str, Any]:
        """Get all state (copy)."""
        return json.loads(json.dumps(self._state))

    def reset_to_defaults(self) -> None:
        """Reset state to defaults."""
        self._state = self._get_default_state()
        self.save()

