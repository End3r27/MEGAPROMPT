"""Schema for final mega-prompt assembly."""

from pydantic import BaseModel, Field


class MegaPrompt(BaseModel):
    """Complete structured mega-prompt."""

    system_role: str = Field(description="Role definition for the AI executing the prompt")
    project_overview: str = Field(description="Concise distilled goal")
    core_requirements: list[str] = Field(description="Bulletproof list of requirements")
    system_architecture: dict[str, dict] = Field(
        description="Detailed architecture for each system with subsections"
    )
    ai_design_rules: list[str] = Field(description="Rules for AI behavior and design")
    unknown_areas: list[str] = Field(description="Explicit list of unresolved unknowns")
    deliverables: dict[str, list[str]] = Field(
        description="Expected deliverables organized by category"
    )
    response_format: list[str] = Field(description="Format requirements for AI responses")

