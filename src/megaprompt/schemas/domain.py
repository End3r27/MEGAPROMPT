"""Schema for domain expansion stage output."""

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("responsibilities", "inputs", "outputs", "failure_modes", "dependencies", mode="before")
    @classmethod
    def normalize_list_field(cls, v) -> list[str]:
        """Normalize list fields to list of strings."""
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
                    text = item.get("text") or item.get("description") or item.get("item") or str(item)
                    normalized.append(str(text))
                else:
                    normalized.append(str(item))
            return normalized
        return [str(v)]


class DomainExpansion(BaseModel):
    """Expanded domain specifications for all systems."""

    systems: dict[str, SystemDetails] = Field(
        description="Map of system names to their detailed specifications"
    )

    @field_validator("systems", mode="before")
    @classmethod
    def normalize_systems(cls, v) -> dict[str, SystemDetails]:
        """Normalize systems dict, handling various input formats."""
        if not isinstance(v, dict):
            return {}

        normalized = {}
        for key, value in v.items():
            # Ensure key is a string
            key_str = str(key)

            # Handle value - could be dict (SystemDetails) or already SystemDetails
            if isinstance(value, dict):
                normalized[key_str] = SystemDetails.model_validate(value)
            elif isinstance(value, SystemDetails):
                normalized[key_str] = value
            else:
                # Try to convert to SystemDetails
                normalized[key_str] = SystemDetails.model_validate({"responsibilities": [], "inputs": [], "outputs": [], "failure_modes": [], "dependencies": []})

        return normalized

