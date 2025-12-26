"""Schemas for codebase analysis."""

from typing import Optional

from pydantic import BaseModel, Field


class CodebaseStructure(BaseModel):
    """Structural information extracted from codebase."""

    modules: list[str] = Field(default_factory=list, description="List of module/package names")
    entry_points: list[str] = Field(
        default_factory=list, description="Entry points (main functions, CLI commands)"
    )
    public_apis: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Public APIs: module -> [functions, classes]",
    )
    core_loops: list[str] = Field(
        default_factory=list, description="Core loops detected (update/tick/main)"
    )
    data_models: list[str] = Field(
        default_factory=list, description="Data models (Pydantic, dataclasses)"
    )
    config_files: list[str] = Field(default_factory=list, description="Configuration files found")
    tests: bool = Field(default=False, description="Whether tests are present")
    persistence: bool = Field(
        default=False, description="Whether persistence layer is detected"
    )
    has_cli: bool = Field(default=False, description="Whether CLI is present")
    has_api: bool = Field(default=False, description="Whether API endpoints are present")
    has_docker: bool = Field(default=False, description="Whether Dockerfile is present")
    has_entrypoint: bool = Field(
        default=False, description="Whether Dockerfile has ENTRYPOINT or CMD"
    )
    has_source_code: bool = Field(
        default=False, description="Whether source code files exist beyond config"
    )
    has_readme: bool = Field(default=False, description="Whether README exists")
    file_count: int = Field(default=0, description="Total number of source files")


class ProjectIntent(BaseModel):
    """Classified intent of the project."""

    intent_type: str = Field(
        description="Intent type: executable_utility, base_image, runtime_environment, build_image, library_image, template, scaffold, unknown"
    )
    confidence: str = Field(
        description="Confidence level: high, medium, low"
    )
    reasoning: str = Field(
        description="Why this intent was classified (heuristics + AI reasoning)"
    )
    is_minimal: bool = Field(
        default=False,
        description="Whether this appears to be an intentionally minimal/foundational project",
    )
    maturity_level: str = Field(
        default="unknown",
        description="Project maturity: foundation, template, prototype, production, unknown",
    )


class ArchitecturalInference(BaseModel):
    """Inferred architectural information about the project."""

    project_type: str = Field(description="Type of project (e.g., 'agent-based simulation', 'web api')")
    dominant_patterns: list[str] = Field(
        default_factory=list, description="Dominant architectural patterns"
    )
    implicit_assumptions: list[str] = Field(
        default_factory=list, description="Implicit assumptions in the design"
    )
    detected_frameworks: list[str] = Field(
        default_factory=list, description="Frameworks and libraries detected"
    )
    architectural_style: str = Field(
        default="", description="Architectural style (e.g., 'monolithic', 'microservices')"
    )


class SystemExpectation(BaseModel):
    """Expected system for a project type."""

    name: str = Field(description="System name")
    category: str = Field(
        description="System category: lifecycle, persistence, error_handling, observability, performance, tooling, testing, extensibility, safety"
    )
    rationale: str = Field(description="Why this system is expected for this project type")
    priority: str = Field(description="Priority: critical, high, medium, low")


class ExpectedSystems(BaseModel):
    """Canonical systems expected for a project type."""

    systems: list[SystemExpectation] = Field(
        default_factory=list, description="List of expected systems"
    )


class SystemGap(BaseModel):
    """A missing or partial system."""

    system: str = Field(description="System name")
    category: str = Field(description="System category")
    priority: str = Field(description="Priority level")
    rationale: str = Field(description="Why this system is needed")
    evidence_searched: list[str] = Field(
        default_factory=list, description="What we searched for as evidence"
    )
    confidence: str = Field(
        default="medium",
        description="Confidence level: high, medium, low - how certain we are this is actually missing vs intentional",
    )
    may_be_intentional: bool = Field(
        default=False,
        description="Whether this gap may be intentional given the project intent",
    )


class SystemHoles(BaseModel):
    """Analysis of missing and partial systems."""

    missing: list[SystemGap] = Field(default_factory=list, description="Missing systems")
    partial: list[SystemGap] = Field(default_factory=list, description="Partially implemented systems")
    present: list[str] = Field(default_factory=list, description="System names that are present")


class Enhancement(BaseModel):
    """A suggested enhancement for the codebase."""

    name: str = Field(description="Enhancement name")
    description: str = Field(description="What the enhancement provides")
    why: str = Field(description="Why it fits the architecture")
    effort: str = Field(description="Implementation effort: low, medium, high")
    risk: str = Field(description="Risk level: low, medium, high")
    fits_existing: bool = Field(
        default=True, description="Whether it fits the existing structure"
    )


class Enhancements(BaseModel):
    """Collection of enhancement suggestions."""

    enhancements: list[Enhancement] = Field(
        default_factory=list, description="List of enhancements"
    )


class DriftItem(BaseModel):
    """An intent drift detection item."""

    original_intent: str = Field(description="What was originally intended")
    current_state: str = Field(description="Current implementation state")
    severity: str = Field(description="Severity: critical, medium, low")


class IntentDrift(BaseModel):
    """Intent drift analysis comparing original design to implementation."""

    drifts: list[DriftItem] = Field(default_factory=list, description="List of drift items")


class AnalysisReport(BaseModel):
    """Complete analysis report."""

    structure: CodebaseStructure
    intent: ProjectIntent
    inference: ArchitecturalInference
    holes: SystemHoles
    enhancements: Enhancements
    intent_drift: Optional[IntentDrift] = Field(
        default=None, description="Intent drift if original prompt provided"
    )

