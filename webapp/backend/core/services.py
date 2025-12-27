"""Service layer for integrating MEGAPROMPT functionality."""

import sys
from pathlib import Path
from typing import Any, Optional

# Add MEGAPROMPT to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from megaprompt.analysis.pipeline import AnalysisPipeline
from megaprompt.core.config import Config
from megaprompt.core.pipeline import MegaPromptPipeline
from megaprompt.core.provider_factory import create_client


class MegaPromptService:
    """Service for MEGAPROMPT operations."""

    @staticmethod
    def create_pipeline(config: dict[str, Any]) -> MegaPromptPipeline:
        """
        Create a MegaPromptPipeline from config dictionary.

        Args:
            config: Configuration dictionary

        Returns:
            MegaPromptPipeline instance
        """
        # Convert config dict to Config object
        config_obj = Config.load(config)

        # Get directories
        checkpoint_dir = None
        if config_obj.checkpoint_dir:
            checkpoint_dir = Path(config_obj.checkpoint_dir)
        elif hasattr(config_obj, "get_checkpoint_dir"):
            checkpoint_dir = config_obj.get_checkpoint_dir()

        cache_dir = None
        if config_obj.cache_dir:
            cache_dir = Path(config_obj.cache_dir)
        elif hasattr(config_obj, "get_cache_dir"):
            cache_dir = config_obj.get_cache_dir()

        # Create pipeline
        pipeline = MegaPromptPipeline(
            provider=config_obj.provider,
            base_url=config_obj.base_url,
            model=config_obj.model,
            temperature=config_obj.temperature,
            seed=config_obj.seed,
            api_key=config_obj.api_key,
            checkpoint_dir=checkpoint_dir,
            cache_dir=cache_dir,
            use_cache=not config.get("no_cache", False),
        )

        return pipeline

    @staticmethod
    def create_analysis_pipeline(config: dict[str, Any]) -> AnalysisPipeline:
        """
        Create an AnalysisPipeline from config dictionary.

        Args:
            config: Configuration dictionary

        Returns:
            AnalysisPipeline instance
        """
        config_obj = Config.load(config)

        # Create LLM client
        base_client = create_client(
            provider=config_obj.provider,
            model=config_obj.model,
            temperature=config_obj.temperature,
            seed=config_obj.seed,
            base_url=config_obj.base_url,
            api_key=config_obj.api_key,
        )

        # Wrap with logging
        from megaprompt.core.llm_wrapper import wrap_client_with_logging

        actual_model = config_obj.model or "default"
        llm_client = wrap_client_with_logging(
            client=base_client,
            provider=config_obj.provider,
            model=actual_model,
            track_costs=True,
        )

        depth = config.get("depth", "high")
        return AnalysisPipeline(llm_client=llm_client, depth=depth, verbose=True)

    @staticmethod
    def generate_prompt(prompt: str, config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """
        Generate mega-prompt.

        Args:
            prompt: User prompt text
            config: Configuration dictionary

        Returns:
            Tuple of (formatted_mega_prompt_text, intermediate_outputs_dict)
        """
        pipeline = MegaPromptService.create_pipeline(config)
        verbose = config.get("verbose", True)
        resume = config.get("resume", False)
        return pipeline.generate(user_prompt=prompt, verbose=verbose, resume=resume)

    @staticmethod
    def analyze_codebase(codebase_path: str, config: dict[str, Any], mode: str = "full") -> dict[str, Any]:
        """
        Analyze codebase.

        Args:
            codebase_path: Path to codebase directory
            config: Configuration dictionary
            mode: Analysis mode

        Returns:
            Analysis report as dictionary
        """
        analysis_pipeline = MegaPromptService.create_analysis_pipeline(config)
        report = analysis_pipeline.analyze(codebase_path)

        # Convert to dictionary
        if hasattr(report, "model_dump"):
            return report.model_dump()
        elif hasattr(report, "dict"):
            return report.dict()
        else:
            return {"error": "Failed to serialize analysis report"}

    @staticmethod
    def get_config() -> dict[str, Any]:
        """Get current configuration."""
        config = Config.load()
        return config.to_dict()

    @staticmethod
    def save_config(config_dict: dict[str, Any]) -> bool:
        """
        Save configuration.

        Args:
            config_dict: Configuration dictionary

        Returns:
            True if successful
        """
        try:
            config = Config.load(config_dict)
            # Save to user config file
            config_path = Path.home() / ".megaprompt" / "config.yaml"
            config.save(config_path, format="yaml")
            return True
        except Exception:
            return False

