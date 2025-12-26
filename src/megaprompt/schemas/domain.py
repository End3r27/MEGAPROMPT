"""Schema for domain expansion stage output."""

from pydantic import BaseModel, Field


class SystemDetails(BaseModel):
    """Detailed specification for a single system."""

    responsibilities: list[str] = Field(
        description="What this system is responsible for"
    )
    inputs: list[str] = Field(
        description="What data or events this system receives as input"
    )
    outputs: list[str] = Field(
        description="What data or events this system produces as output"
    )
    failure_modes: list[str] = Field(
        description="How this system can fail and what happens when it does"
    )
    dependencies: list[str] = Field(
        description="Other systems or external components this system depends on"
    )


class DomainExpansion(BaseModel):
    """Expanded domain specifications for all systems."""

    systems: dict[str, SystemDetails] = Field(
        description="Map of system names to their detailed specifications"
    )

