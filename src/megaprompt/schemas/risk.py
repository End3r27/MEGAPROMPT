"""Schema for risk analysis stage output."""

from pydantic import BaseModel, Field, field_validator


class RiskAnalysis(BaseModel):
    """Analysis of unknowns and risks in the project."""

    unknowns: list[str] = Field(
        description="Parts of the project that are underspecified or unclear"
    )
    risk_points: list[str] = Field(
        description="Potential failure points, scaling issues, or technical challenges"
    )

    @field_validator("unknowns", mode="before")
    @classmethod
    def normalize_unknowns(cls, v) -> list[str]:
        """Normalize unknowns to list of strings."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            normalized = []
            for item in v:
                if isinstance(item, str):
                    normalized.append(item)
                elif isinstance(item, dict):
                    # Extract text from dict if present
                    text = item.get("text") or item.get("unknown") or item.get("description") or str(item)
                    normalized.append(str(text))
                else:
                    normalized.append(str(item))
            return normalized
        return [str(v)]

    @field_validator("risk_points", mode="before")
    @classmethod
    def normalize_risk_points(cls, v) -> list[str]:
        """Normalize risk_points to list of strings."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            normalized = []
            for item in v:
                if isinstance(item, str):
                    normalized.append(item)
                elif isinstance(item, dict):
                    # Extract text from dict if present
                    text = item.get("text") or item.get("risk") or item.get("description") or str(item)
                    normalized.append(str(text))
                else:
                    normalized.append(str(item))
            return normalized
        return [str(v)]

