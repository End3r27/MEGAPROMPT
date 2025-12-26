"""Schema for constraint enforcement stage output."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Union


class Constraints(BaseModel):
    """Technical constraints for the project."""

    engine: Optional[str] = Field(
        default=None,
        description="Specific engine or framework to use (e.g., 'Godot', 'Unity', 'Django')"
    )
    language: Optional[str] = Field(
        default=None,
        description="Programming language(s) to use (e.g., 'Python', 'GDScript', 'TypeScript'). Use comma-separated string if multiple."
    )

    @field_validator("language", mode="before")
    @classmethod
    def normalize_language(cls, v: Union[str, list, None]) -> Optional[str]:
        """Normalize language field to string."""
        if v is None:
            return None
        if isinstance(v, list):
            # Join list items with comma
            return ", ".join(str(item) for item in v)
        return str(v)

    @field_validator("engine", mode="before")
    @classmethod
    def normalize_engine(cls, v: Union[str, list, None]) -> Optional[str]:
        """Normalize engine field to string."""
        if v is None:
            return None
        if isinstance(v, list):
            # Join list items with comma
            return ", ".join(str(item) for item in v)
        return str(v)
    ai_execution: str = Field(
        default="local only",
        description="Where AI should run: 'local only', 'cloud', 'hybrid'"
    )
    determinism: bool = Field(
        default=True,
        description="Whether the system must be deterministic"
    )
    performance_limits: Optional[list[str]] = Field(
        default=None,
        description="Performance constraints or limits (e.g., 'Must handle 1000+ agents', 'Response time < 100ms')"
    )
    modularity: Optional[str] = Field(
        default=None,
        description="Modularity requirements (e.g., 'fully modular', 'loosely coupled')"
    )
    offline_capable: Optional[bool] = Field(
        default=None,
        description="Whether the system must work offline"
    )

