"""Schema for project decomposition stage output."""

from pydantic import BaseModel, Field, field_validator


class ProjectDecomposition(BaseModel):
    """Decomposed project into orthogonal systems."""

    systems: list[str] = Field(
        description="List of system names. Each system should be a separate, orthogonal concern with clear boundaries"
    )

    @field_validator("systems", mode="before")
    @classmethod
    def normalize_systems(cls, v) -> list[str]:
        """Normalize systems to list of strings."""
        if not isinstance(v, list):
            return v
        
        normalized = []
        for item in v:
            if isinstance(item, str):
                normalized.append(item)
            elif isinstance(item, dict):
                # Extract name from dict (try common field names)
                name = item.get("name") or item.get("system") or item.get("title")
                if name:
                    normalized.append(str(name))
                else:
                    # Fallback: use string representation
                    normalized.append(str(item))
            else:
                # Convert other types to string
                normalized.append(str(item))
        
        return normalized

