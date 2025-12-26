"""Schema for intent extraction stage output."""

from typing import Union

from pydantic import BaseModel, Field, field_validator


class IntentExtraction(BaseModel):
    """Extracted intent from user prompt."""

    project_type: str = Field(
        description="The type of project (e.g., 'simulation game', 'web application', 'data analysis tool')"
    )
    core_goal: str = Field(
        description="The primary objective or goal of the project in one clear sentence"
    )
    user_expectations: list[str] = Field(
        default_factory=list,
        description="List of key expectations or requirements the user has"
    )
    non_goals: list[str] = Field(
        default_factory=list,
        description="Explicitly stated things this project should NOT do or include"
    )

    @field_validator("user_expectations", mode="before")
    @classmethod
    def normalize_expectations(cls, v) -> list[str]:
        """Normalize user_expectations to list of strings."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) if not isinstance(item, str) else item for item in v]
        return [str(v)]

    @field_validator("non_goals", mode="before")
    @classmethod
    def normalize_non_goals(cls, v) -> list[str]:
        """Normalize non_goals to list of strings."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) if not isinstance(item, str) else item for item in v]
        return [str(v)]

