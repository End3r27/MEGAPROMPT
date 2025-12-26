"""Configuration management for MEGAPROMPT."""

import json
import os
from pathlib import Path
from typing import Any, Optional

import yaml


class Config:
    """Configuration manager with hierarchy: CLI args > project config > user config > defaults."""

    def __init__(self):
        """Initialize configuration with default values."""
        self.provider: str = "auto"
        self.model: Optional[str] = None
        self.temperature: float = 0.0
        self.seed: Optional[int] = None
        self.base_url: Optional[str] = None
        self.api_key: Optional[str] = None
        self.verbose: bool = True
        self.output_format: str = "markdown"
        self.checkpoint_dir: Optional[str] = None
        self.cache_dir: Optional[str] = None
        self.template_dir: Optional[str] = None

    @classmethod
    def load(cls, cli_args: Optional[dict[str, Any]] = None) -> "Config":
        """
        Load configuration from hierarchy: CLI args > project config > user config > defaults.

        Args:
            cli_args: Dictionary of CLI arguments to override config

        Returns:
            Config instance with loaded values
        """
        config = cls()

        # Load user config (~/.megaprompt/config.yaml)
        user_config_path = Path.home() / ".megaprompt" / "config.yaml"
        if user_config_path.exists():
            config._load_file(user_config_path, config)

        # Load project config (.megaprompt.yaml in current directory)
        project_config_path = Path.cwd() / ".megaprompt.yaml"
        if project_config_path.exists():
            config._load_file(project_config_path, config)

        # Override with CLI args
        if cli_args:
            for key, value in cli_args.items():
                if value is not None:
                    setattr(config, key, value)

        return config

    def _load_file(self, config_path: Path, config: "Config") -> None:
        """Load configuration from a YAML or JSON file."""
        try:
            content = config_path.read_text(encoding="utf-8")
            if config_path.suffix in [".yaml", ".yml"]:
                data = yaml.safe_load(content)
            elif config_path.suffix == ".json":
                data = json.loads(content)
            else:
                return  # Skip unknown formats

            if not isinstance(data, dict):
                return

            # Apply config values
            for key, value in data.items():
                if hasattr(config, key) and value is not None:
                    setattr(config, key, value)
        except Exception:
            # Silently fail on config load errors
            pass

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "seed": self.seed,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "verbose": self.verbose,
            "output_format": self.output_format,
            "checkpoint_dir": self.checkpoint_dir,
            "cache_dir": self.cache_dir,
            "template_dir": self.template_dir,
        }

    def save(self, path: Path, format: str = "yaml") -> None:
        """
        Save configuration to file.

        Args:
            path: Path to save config file
            format: Format to save as ('yaml' or 'json')
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()

        # Remove None values for cleaner config
        data = {k: v for k, v in data.items() if v is not None}

        if format == "yaml":
            content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        else:
            content = json.dumps(data, indent=2)

        path.write_text(content, encoding="utf-8")

    def get_checkpoint_dir(self) -> Path:
        """Get checkpoint directory, creating it if needed."""
        if self.checkpoint_dir:
            dir_path = Path(self.checkpoint_dir)
        else:
            dir_path = Path.home() / ".megaprompt" / "checkpoints"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def get_cache_dir(self) -> Path:
        """Get cache directory, creating it if needed."""
        if self.cache_dir:
            dir_path = Path(self.cache_dir)
        else:
            dir_path = Path.home() / ".megaprompt" / "cache"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

