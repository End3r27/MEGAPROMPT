"""MEGAPROMPT Core Interface - API layer wrapping existing MEGAPROMPT functionality."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from megaprompt.analysis.pipeline import AnalysisPipeline
from megaprompt.core.config import Config
from megaprompt.core.pipeline import MegaPromptPipeline
from megaprompt.core.provider_factory import create_client

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Error type enumeration."""

    NETWORK_TIMEOUT = "network_timeout"
    CONNECTION_UNAVAILABLE = "connection_unavailable"
    INVALID_CREDENTIALS = "invalid_credentials"
    MALFORMED_REQUEST = "malformed_request"
    RATE_LIMIT = "rate_limit"
    VERSION_MISMATCH = "version_mismatch"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class Error:
    """Error information."""

    type: ErrorType
    message: str
    details: Optional[dict[str, Any]] = None
    retry_after: Optional[int] = None  # For rate limit errors


@dataclass
class ProgressInfo:
    """Progress information."""

    stage: str
    message: str
    progress: float  # 0.0 to 1.0
    current: Optional[int] = None
    total: Optional[int] = None


class Result:
    """Result type for success/error handling."""

    def __init__(self, success: bool, value: Any = None, error: Optional[Error] = None):
        self.success = success
        self.value = value
        self.error = error

    @classmethod
    def ok(cls, value: Any) -> "Result":
        """Create a successful result."""
        return cls(success=True, value=value)

    @classmethod
    def err(cls, error: Error) -> "Result":
        """Create an error result."""
        return cls(success=False, error=error)

    def is_ok(self) -> bool:
        """Check if result is successful."""
        return self.success

    def is_err(self) -> bool:
        """Check if result is an error."""
        return not self.success


class MegaPromptCoreInterface:
    """Core interface wrapping MEGAPROMPT functionality."""

    def __init__(self):
        """Initialize the core interface."""
        self._current_pipeline: Optional[MegaPromptPipeline] = None
        self._current_analysis: Optional[AnalysisPipeline] = None
        self._progress_info: Optional[ProgressInfo] = None
        self._config: Optional[Config] = None

    def _create_pipeline(self, config_dict: dict[str, Any]) -> MegaPromptPipeline:
        """Create a MegaPromptPipeline from config dictionary."""
        # Convert config dict to Config object
        config = Config.load(config_dict)

        # Create pipeline with config
        checkpoint_dir = None
        if config.checkpoint_dir:
            checkpoint_dir = Path(config.checkpoint_dir)
        elif config.get_checkpoint_dir():
            checkpoint_dir = config.get_checkpoint_dir()

        cache_dir = None
        if config.cache_dir:
            cache_dir = Path(config.cache_dir)
        elif config.get_cache_dir():
            cache_dir = config.get_cache_dir()

        pipeline = MegaPromptPipeline(
            provider=config.provider,
            base_url=config.base_url,
            model=config.model,
            temperature=config.temperature,
            seed=config.seed,
            api_key=config.api_key,
            checkpoint_dir=checkpoint_dir,
            cache_dir=cache_dir,
            use_cache=True,
        )

        return pipeline

    def _create_analysis_pipeline(self, config_dict: dict[str, Any]) -> AnalysisPipeline:
        """Create an AnalysisPipeline from config dictionary."""
        config = Config.load(config_dict)

        # Create LLM client
        base_client = create_client(
            provider=config.provider,
            model=config.model,
            temperature=config.temperature,
            seed=config.seed,
            base_url=config.base_url,
            api_key=config.api_key,
        )

        # Wrap with logging
        from megaprompt.core.llm_wrapper import wrap_client_with_logging

        actual_model = config.model or "default"
        llm_client = wrap_client_with_logging(
            client=base_client,
            provider=config.provider,
            model=actual_model,
            track_costs=True,
        )

        return AnalysisPipeline(llm_client=llm_client, depth="high", verbose=True)

    def generate_prompt(self, user_prompt: str, config: dict[str, Any]) -> Result[str]:
        """
        Generate mega-prompt from user input.

        Args:
            user_prompt: User prompt text
            config: Configuration dictionary

        Returns:
            Result containing generated prompt text or error
        """
        try:
            # Validate input
            if not user_prompt or not user_prompt.strip():
                return Result.err(
                    Error(
                        type=ErrorType.MALFORMED_REQUEST,
                        message="User prompt cannot be empty",
                    )
                )

            # Validate config
            validation_result = self.validate_config(config)
            if validation_result.is_err():
                return validation_result

            # Create pipeline
            try:
                pipeline = self._create_pipeline(config)
            except Exception as e:
                logger.error(f"Failed to create pipeline: {e}", exc_info=True)
                return Result.err(
                    Error(
                        type=ErrorType.VERSION_MISMATCH,
                        message=f"Failed to initialize pipeline: {str(e)}",
                        details={"exception": str(e)},
                    )
                )

            # Generate prompt
            try:
                self._current_pipeline = pipeline
                result_text, intermediate_outputs = pipeline.generate(
                    user_prompt=user_prompt,
                    verbose=config.get("verbose", True),
                    resume=config.get("resume", False),
                )
                return Result.ok(result_text)
            except RuntimeError as e:
                error_msg = str(e).lower()
                if "timeout" in error_msg or "connection" in error_msg:
                    return Result.err(
                        Error(
                            type=ErrorType.CONNECTION_UNAVAILABLE,
                            message=f"Connection unavailable: {str(e)}",
                            details={"exception": str(e)},
                        )
                    )
                elif "authentication" in error_msg or "credentials" in error_msg or "401" in error_msg:
                    return Result.err(
                        Error(
                            type=ErrorType.INVALID_CREDENTIALS,
                            message=f"Invalid credentials: {str(e)}",
                            details={"exception": str(e)},
                        )
                    )
                elif "rate limit" in error_msg or "429" in error_msg:
                    # Try to extract retry-after from error
                    retry_after = None
                    if "retry-after" in error_msg:
                        # Parse retry-after if present
                        pass  # Could implement parsing here
                    return Result.err(
                        Error(
                            type=ErrorType.RATE_LIMIT,
                            message=f"Rate limit exceeded: {str(e)}",
                            details={"exception": str(e)},
                            retry_after=retry_after,
                        )
                    )
                else:
                    return Result.err(
                        Error(
                            type=ErrorType.UNKNOWN_ERROR,
                            message=f"Generation failed: {str(e)}",
                            details={"exception": str(e)},
                        )
                    )
            except ValueError as e:
                return Result.err(
                    Error(
                        type=ErrorType.MALFORMED_REQUEST,
                        message=f"Invalid input: {str(e)}",
                        details={"exception": str(e)},
                    )
                )
        except Exception as e:
            logger.error(f"Unexpected error in generate_prompt: {e}", exc_info=True)
            return Result.err(
                Error(
                    type=ErrorType.UNKNOWN_ERROR,
                    message=f"Unexpected error: {str(e)}",
                    details={"exception": str(e)},
                )
            )

    def analyze_codebase(self, codebase_path: str, config: dict[str, Any], mode: str = "full") -> Result[dict[str, Any]]:
        """
        Analyze codebase and return analysis report.

        Args:
            codebase_path: Path to codebase directory
            config: Configuration dictionary
            mode: Analysis mode ('full', 'systems', 'holes', 'enhancements')

        Returns:
            Result containing analysis report dictionary or error
        """
        try:
            # Validate input
            path = Path(codebase_path)
            if not path.exists() or not path.is_dir():
                return Result.err(
                    Error(
                        type=ErrorType.MALFORMED_REQUEST,
                        message=f"Codebase path does not exist or is not a directory: {codebase_path}",
                    )
                )

            # Validate config
            validation_result = self.validate_config(config)
            if validation_result.is_err():
                return validation_result

            # Create analysis pipeline
            try:
                analysis_pipeline = self._create_analysis_pipeline(config)
            except Exception as e:
                logger.error(f"Failed to create analysis pipeline: {e}", exc_info=True)
                return Result.err(
                    Error(
                        type=ErrorType.VERSION_MISMATCH,
                        message=f"Failed to initialize analysis pipeline: {str(e)}",
                        details={"exception": str(e)},
                    )
                )

            # Run analysis
            try:
                self._current_analysis = analysis_pipeline
                report = analysis_pipeline.analyze(codebase_path)
                # Convert report to dictionary
                report_dict = report.model_dump() if hasattr(report, "model_dump") else report.dict()
                return Result.ok(report_dict)
            except RuntimeError as e:
                error_msg = str(e).lower()
                if "timeout" in error_msg or "connection" in error_msg:
                    return Result.err(
                        Error(
                            type=ErrorType.CONNECTION_UNAVAILABLE,
                            message=f"Connection unavailable: {str(e)}",
                            details={"exception": str(e)},
                        )
                    )
                elif "authentication" in error_msg or "credentials" in error_msg:
                    return Result.err(
                        Error(
                            type=ErrorType.INVALID_CREDENTIALS,
                            message=f"Invalid credentials: {str(e)}",
                            details={"exception": str(e)},
                        )
                    )
                else:
                    return Result.err(
                        Error(
                            type=ErrorType.UNKNOWN_ERROR,
                            message=f"Analysis failed: {str(e)}",
                            details={"exception": str(e)},
                        )
                    )
        except Exception as e:
            logger.error(f"Unexpected error in analyze_codebase: {e}", exc_info=True)
            return Result.err(
                Error(
                    type=ErrorType.UNKNOWN_ERROR,
                    message=f"Unexpected error: {str(e)}",
                    details={"exception": str(e)},
                )
            )

    def validate_config(self, config: dict[str, Any]) -> Result[bool]:
        """
        Validate configuration dictionary.

        Args:
            config: Configuration dictionary

        Returns:
            Result indicating if config is valid
        """
        try:
            # Try to create a Config object to validate
            Config.load(config)
            return Result.ok(True)
        except Exception as e:
            return Result.err(
                Error(
                    type=ErrorType.MALFORMED_REQUEST,
                    message=f"Invalid configuration: {str(e)}",
                    details={"exception": str(e)},
                )
            )

    def get_progress(self) -> Optional[ProgressInfo]:
        """
        Get current operation progress.

        Returns:
            ProgressInfo if available, None otherwise
        """
        return self._progress_info

    def set_progress(self, stage: str, message: str, progress: float, current: Optional[int] = None, total: Optional[int] = None) -> None:
        """Set progress information."""
        self._progress_info = ProgressInfo(stage=stage, message=message, progress=progress, current=current, total=total)

