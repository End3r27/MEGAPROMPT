"""Schema for risk analysis stage output."""

from pydantic import BaseModel, Field


class RiskAnalysis(BaseModel):
    """Analysis of unknowns and risks in the project."""

    unknowns: list[str] = Field(
        description="Parts of the project that are underspecified or unclear"
    )
    risk_points: list[str] = Field(
        description="Potential failure points, scaling issues, or technical challenges"
    )

