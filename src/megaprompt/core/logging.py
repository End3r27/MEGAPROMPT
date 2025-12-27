"""Structured logging and observability system for MEGAPROMPT."""

import json
import logging
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    JSON_LOGGER_AVAILABLE = False


class LogLevel(str, Enum):
    """Log level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        
        # Add any extra fields from the record
        # Exclude standard LogRecord attributes
        standard_attrs = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message',
            'pathname', 'process', 'processName', 'relativeCreated', 'thread',
            'threadName', 'exc_info', 'exc_text', 'stack_info'
        }
        
        for key, value in record.__dict__.items():
            if key not in standard_attrs:
                log_data[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class StructuredLogger:
    """
    Structured logger with JSON output support and context tracking.
    
    Provides configurable logging with structured JSON output for production
    debugging, token usage tracking, pipeline stage monitoring, and LLM interaction logging.
    """

    def __init__(
        self,
        name: str = "megaprompt",
        level: LogLevel = LogLevel.INFO,
        json_output: bool = False,
        log_file: Optional[Path] = None,
    ):
        """
        Initialize structured logger.

        Args:
            name: Logger name
            level: Log level
            json_output: If True, output JSON-formatted logs
            log_file: Optional file path to write logs to
        """
        self.name = name
        self.level = level
        self.json_output = json_output
        self.log_file = log_file
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.value))
        self.logger.propagate = False
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # Create formatter
        if json_output:
            if JSON_LOGGER_AVAILABLE:
                formatter = jsonlogger.JsonFormatter(
                    "%(timestamp)s %(level)s %(name)s %(message)s",
                    timestamp=True,
                )
            else:
                # Fallback to custom JSON formatter if pythonjsonlogger not available
                formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(getattr(logging, level.value))
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, level.value))
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def _log_with_context(
        self,
        level: int,
        message: str,
        context: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log message with additional context.

        Args:
            level: Log level (logging.DEBUG, etc.)
            message: Log message
            context: Additional context dictionary
            **kwargs: Additional keyword arguments to include in log
        """
        if context:
            kwargs.update(context)
        
        if kwargs:
            # Create log record with extra fields
            record = self.logger.makeRecord(
                self.logger.name, level, "", 0, message, (), None
            )
            # Add context fields to the record
            for key, value in kwargs.items():
                setattr(record, key, value)
            self.logger.handle(record)
        else:
            self.logger.log(level, message)
    
    def debug(self, message: str, context: Optional[dict[str, Any]] = None, **kwargs: Any) -> None:
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, context, **kwargs)
    
    def info(self, message: str, context: Optional[dict[str, Any]] = None, **kwargs: Any) -> None:
        """Log info message."""
        self._log_with_context(logging.INFO, message, context, **kwargs)
    
    def warning(self, message: str, context: Optional[dict[str, Any]] = None, **kwargs: Any) -> None:
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, context, **kwargs)
    
    def error(self, message: str, context: Optional[dict[str, Any]] = None, **kwargs: Any) -> None:
        """Log error message."""
        self._log_with_context(logging.ERROR, message, context, **kwargs)
    
    def critical(self, message: str, context: Optional[dict[str, Any]] = None, **kwargs: Any) -> None:
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, context, **kwargs)
    
    def log_llm_call(
        self,
        provider: str,
        model: str,
        prompt: str,
        response: str,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        latency_ms: Optional[float] = None,
        cost: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log LLM API call with structured metadata.

        Args:
            provider: LLM provider name (e.g., "openai", "gemini")
            model: Model name
            prompt: Input prompt (may be truncated in logs)
            response: Response text (may be truncated in logs)
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            latency_ms: Request latency in milliseconds
            cost: Estimated cost in dollars
            **kwargs: Additional metadata
        """
        # Truncate long prompts/responses for logging
        prompt_preview = prompt[:200] + "..." if len(prompt) > 200 else prompt
        response_preview = response[:200] + "..." if len(response) > 200 else response
        
        context = {
            "event_type": "llm_call",
            "provider": provider,
            "model": model,
            "prompt_length": len(prompt),
            "response_length": len(response),
            "prompt_preview": prompt_preview,
            "response_preview": response_preview,
        }
        
        if tokens_input is not None:
            context["tokens_input"] = tokens_input
        if tokens_output is not None:
            context["tokens_output"] = tokens_output
        if latency_ms is not None:
            context["latency_ms"] = latency_ms
        if cost is not None:
            context["cost"] = cost
        
        context.update(kwargs)
        
        self.info(f"LLM call: {provider}/{model}", context=context)
    
    def log_pipeline_stage(
        self,
        stage: str,
        status: str,
        duration_ms: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log pipeline stage execution.

        Args:
            stage: Stage name (e.g., "intent_extraction", "project_decomposition")
            status: Status ("started", "completed", "failed")
            duration_ms: Stage duration in milliseconds
            **kwargs: Additional metadata
        """
        context = {
            "event_type": "pipeline_stage",
            "stage": stage,
            "status": status,
        }
        
        if duration_ms is not None:
            context["duration_ms"] = duration_ms
        
        context.update(kwargs)
        
        if status == "failed":
            self.error(f"Pipeline stage {stage} failed", context=context)
        elif status == "completed":
            self.info(f"Pipeline stage {stage} completed", context=context)
        else:
            self.info(f"Pipeline stage {stage} started", context=context)
    
    def log_token_usage(
        self,
        provider: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
        cost: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log token usage and cost.

        Args:
            provider: LLM provider name
            model: Model name
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            cost: Estimated cost in dollars
            **kwargs: Additional metadata
        """
        context = {
            "event_type": "token_usage",
            "provider": provider,
            "model": model,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "tokens_total": tokens_input + tokens_output,
        }
        
        if cost is not None:
            context["cost"] = cost
        
        context.update(kwargs)
        
        self.info(f"Token usage: {tokens_input + tokens_output} tokens", context=context)


# Global logger instance
_default_logger: Optional[StructuredLogger] = None


def get_logger(
    name: str = "megaprompt",
    level: Optional[LogLevel] = None,
    json_output: Optional[bool] = None,
    log_file: Optional[Path] = None,
) -> StructuredLogger:
    """
    Get or create a structured logger instance.

    Args:
        name: Logger name
        level: Log level (if None, uses default or existing logger's level)
        json_output: If True, output JSON-formatted logs (if None, uses existing setting)
        log_file: Optional file path to write logs to

    Returns:
        StructuredLogger instance
    """
    global _default_logger
    
    if _default_logger is None:
        _default_logger = StructuredLogger(
            name=name,
            level=level or LogLevel.INFO,
            json_output=json_output or False,
            log_file=log_file,
        )
    else:
        # Update settings if provided
        if level is not None:
            _default_logger.level = level
            _default_logger.logger.setLevel(getattr(logging, level.value))
        if json_output is not None:
            _default_logger.json_output = json_output
        if log_file is not None and _default_logger.log_file != log_file:
            # Add file handler if different file specified
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, _default_logger.level.value))
            if _default_logger.json_output:
                if JSON_LOGGER_AVAILABLE:
                    formatter = jsonlogger.JsonFormatter(
                        "%(timestamp)s %(level)s %(name)s %(message)s",
                        timestamp=True,
                    )
                else:
                    formatter = JSONFormatter()
            else:
                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            file_handler.setFormatter(formatter)
            _default_logger.logger.addHandler(file_handler)
            _default_logger.log_file = log_file
    
    return _default_logger


def configure_logging(
    level: str = "INFO",
    json_output: bool = False,
    log_file: Optional[str] = None,
) -> StructuredLogger:
    """
    Configure global logging settings.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: If True, output JSON-formatted logs
        log_file: Optional file path to write logs to

    Returns:
        Configured StructuredLogger instance
    """
    log_level = LogLevel[level.upper()]
    log_path = Path(log_file) if log_file else None
    
    return get_logger(
        level=log_level,
        json_output=json_output,
        log_file=log_path,
    )

