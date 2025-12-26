"""JSON schema validation utilities."""

import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from megaprompt.core.llm_base import LLMClientBase


def _format_validation_error(error: ValidationError, schema_class: type[BaseModel]) -> str:
    """
    Format validation error with actionable suggestions.

    Args:
        error: Pydantic ValidationError
        schema_class: The schema class that failed validation

    Returns:
        Formatted error message with suggestions
    """
    errors = error.errors()
    if not errors:
        return str(error)

    error_parts = [f"Validation failed for {schema_class.__name__}:"]
    error_parts.append("")

    for err in errors:
        loc = " -> ".join(str(x) for x in err["loc"])
        error_type = err["type"]
        input_value = err.get("input")
        msg = err.get("msg", "")

        error_parts.append(f"Field: {loc}")
        error_parts.append(f"  Error: {msg}")
        error_parts.append(f"  Type: {error_type}")

        # Provide suggestions based on error type
        suggestions = []
        if error_type == "string_type":
            if isinstance(input_value, dict):
                # Check if it's a dict with a 'name' field (common LLM response pattern)
                if "name" in input_value:
                    suggestions.append(
                        f"  Suggestion: Expected string but got dict with 'name' field. "
                        f"Did you mean to extract the 'name' field? Try: {input_value.get('name')}"
                    )
                elif "system" in input_value:
                    suggestions.append(
                        f"  Suggestion: Expected string but got dict with 'system' field. "
                        f"Did you mean to extract the 'system' field? Try: {input_value.get('system')}"
                    )
                elif "title" in input_value:
                    suggestions.append(
                        f"  Suggestion: Expected string but got dict with 'title' field. "
                        f"Did you mean to extract the 'title' field? Try: {input_value.get('title')}"
                    )
                else:
                    suggestions.append(
                        "  Suggestion: Expected string but got dict. "
                        "Extract a string value from the dict (e.g., use 'name', 'system', or 'title' field)."
                    )
            elif isinstance(input_value, list):
                suggestions.append(
                    "  Suggestion: Expected string but got list. "
                    "Use a single string value, or extract the first item if appropriate."
                )
        elif error_type == "list_type":
            if isinstance(input_value, str):
                suggestions.append(
                    "  Suggestion: Expected list but got string. "
                    "Wrap the value in a list: [value]"
                )
            elif isinstance(input_value, dict):
                suggestions.append(
                    "  Suggestion: Expected list but got dict. "
                    "Convert to list format or extract list values from the dict."
                )
        elif error_type == "dict_type":
            if isinstance(input_value, list):
                suggestions.append(
                    "  Suggestion: Expected dict but got list. "
                    "Convert list items to dict format or use a single dict."
                )
        elif error_type == "missing":
            suggestions.append(
                f"  Suggestion: Required field '{loc}' is missing. "
                f"Add this field to the input data."
            )

        if suggestions:
            error_parts.extend(suggestions)

        # Show input value (truncated if too long)
        if input_value is not None:
            input_str = str(input_value)
            if len(input_str) > 100:
                input_str = input_str[:97] + "..."
            error_parts.append(f"  Input value: {input_str}")

        error_parts.append("")

    # Add example structure
    try:
        # Try to get field info from schema
        schema_fields = schema_class.model_fields
        if schema_fields:
            error_parts.append("Expected structure example:")
            example = {}
            for field_name, field_info in list(schema_fields.items())[:5]:  # Show first 5 fields
                field_type = field_info.annotation
                if hasattr(field_type, "__origin__"):
                    # Handle generic types
                    if "list" in str(field_type).lower():
                        example[field_name] = ["example_value"]
                    elif "dict" in str(field_type).lower():
                        example[field_name] = {"key": "value"}
                    else:
                        example[field_name] = "example_value"
                elif "str" in str(field_type).lower():
                    example[field_name] = "example_string"
                elif "list" in str(field_type).lower():
                    example[field_name] = ["example_item"]
                else:
                    example[field_name] = "example_value"
            error_parts.append(f"  {json.dumps(example, indent=2)}")
    except Exception:
        pass  # Skip example if we can't generate it

    return "\n".join(error_parts)


def validate_schema(
    data: dict[str, Any],
    schema_class: type[BaseModel],
    llm_client: Optional[LLMClientBase] = None,
    original_prompt: Optional[str] = None,
    max_retries: int = 1,
) -> BaseModel:
    """
    Validate data against a Pydantic schema, with optional retry and correction.

    Args:
        data: Dictionary to validate
        schema_class: Pydantic model class to validate against
        llm_client: Optional LLM client for correction retries
        original_prompt: Original prompt that generated the data (for correction)
        max_retries: Maximum number of correction retries (default: 1)

    Returns:
        Validated model instance

    Raises:
        ValueError: If validation fails with detailed error message
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return schema_class.model_validate(data)
        except ValidationError as e:
            last_error = e
            formatted_error = _format_validation_error(e, schema_class)

            # Try to correct if we have LLM client and original prompt
            if attempt < max_retries and llm_client and original_prompt:
                try:
                    correction_prompt = f"""The previous response failed validation. Please correct it.

Original prompt:
{original_prompt}

Validation errors:
{formatted_error}

Current (incorrect) response:
{json.dumps(data, indent=2)}

Please provide a corrected JSON response that matches the expected schema. Only return the JSON object, no other text."""
                    
                    corrected_response = llm_client.generate(correction_prompt)
                    corrected_data = llm_client.extract_json(corrected_response)
                    data = corrected_data  # Use corrected data for next attempt
                    continue
                except Exception:
                    # If correction fails, break and raise original error
                    break

    # If we get here, validation failed and correction didn't work (or wasn't attempted)
    formatted_error = _format_validation_error(last_error, schema_class)
    raise ValueError(formatted_error) from last_error

