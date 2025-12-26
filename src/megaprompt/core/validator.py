"""JSON schema validation utilities."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError


def validate_schema(data: dict[str, Any], schema_class: type[BaseModel]) -> BaseModel:
    """
    Validate data against a Pydantic schema.

    Args:
        data: Dictionary to validate
        schema_class: Pydantic model class to validate against

    Returns:
        Validated model instance

    Raises:
        ValidationError: If validation fails
    """
    try:
        return schema_class.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Validation failed: {e}") from e

