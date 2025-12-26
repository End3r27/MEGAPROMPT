"""Schema for intent extraction stage output."""

from pydantic import BaseModel, Field


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

