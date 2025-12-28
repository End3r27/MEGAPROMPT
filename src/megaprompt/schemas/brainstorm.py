"""Schema for brainstorm pipeline stages."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class IdeaSpaceExpansion(BaseModel):
    """Concept axes identification for idea generation."""

    axes: list[str] = Field(
        description="Concept dimensions that will guide idea generation to ensure diversity",
        min_length=3,
        max_length=10,
    )
    rationale: str = Field(
        description="Explanation of why these axes ensure diverse idea generation"
    )

    @field_validator("axes", mode="before")
    @classmethod
    def normalize_axes(cls, v) -> list[str]:
        """Normalize axes to list of strings."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) if not isinstance(item, str) else item for item in v]
        return [str(v)]


class ConceptCluster(BaseModel):
    """A cluster grouping related concept axes."""

    name: str = Field(description="Name of the cluster")
    description: str = Field(description="Description of what this cluster represents")
    axis_combination: list[str] = Field(
        description="Which axes from the idea space this cluster represents"
    )

    @field_validator("axis_combination", mode="before")
    @classmethod
    def normalize_axis_combination(cls, v) -> list[str]:
        """Normalize axis_combination to list of strings."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) if not isinstance(item, str) else item for item in v]
        return [str(v)]


class ConceptClusters(BaseModel):
    """Grouped concept clusters from idea space."""

    clusters: list[ConceptCluster] = Field(
        description="List of concept clusters, each representing a different idea direction",
        min_length=1,
    )

    @field_validator("clusters", mode="before")
    @classmethod
    def normalize_clusters(cls, v) -> list[ConceptCluster]:
        """Normalize clusters to list of ConceptCluster."""
        if v is None:
            return []
        if isinstance(v, list):
            return [
                item if isinstance(item, ConceptCluster) else ConceptCluster(**item)
                for item in v
            ]
        return []


class ProjectIdea(BaseModel):
    """Structured project idea schema."""

    name: str = Field(description="Name of the project idea")
    tagline: str = Field(
        description="One-sentence tagline that captures the essence of the idea"
    )
    core_loop: list[str] = Field(
        description="List of steps that define the core gameplay/interaction loop",
        min_length=2,
    )
    key_systems: list[str] = Field(
        description="List of key systems or components required",
        min_length=2,
    )
    unique_twist: str = Field(
        description="What makes this idea unique or different from similar projects"
    )
    technical_challenge: str = Field(
        description="The main technical challenge or complexity this idea faces"
    )
    feasibility: Literal["low", "medium", "high"] = Field(
        description="Estimated feasibility of building this project"
    )
    why_it_exists: str = Field(
        description="Reason or motivation for why this project should exist"
    )
    potential_failures: list[str] = Field(
        description="List of ways this idea might fail or challenges it might face",
        default_factory=list,
    )
    estimated_scope: Literal["small", "medium", "large"] = Field(
        description="Estimated scope/size of the project"
    )

    @field_validator("core_loop", "key_systems", "potential_failures", mode="before")
    @classmethod
    def normalize_list_field(cls, v) -> list[str]:
        """Normalize list fields to list of strings."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) if not isinstance(item, str) else item for item in v]
        return [str(v)]


class BrainstormResult(BaseModel):
    """Final brainstorm output with ideas and metadata."""

    seed_prompt: str = Field(description="The original seed prompt that started the brainstorm")
    ideas: list[ProjectIdea] = Field(
        description="List of generated project ideas",
        min_length=1,
    )
    metadata: dict[str, Any] = Field(
        description="Metadata about the brainstorm (count, diversity score, etc.)",
        default_factory=dict,
    )

