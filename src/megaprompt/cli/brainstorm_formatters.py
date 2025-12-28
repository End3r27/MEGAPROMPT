"""Formatters for brainstorm output."""

import json
from typing import Any

from megaprompt.schemas.brainstorm import BrainstormResult, ProjectIdea


def format_brainstorm_output(result: BrainstormResult, format_type: str) -> str:
    """
    Format brainstorm result as markdown or JSON.

    Args:
        result: The brainstorm result to format
        format_type: Format type ('markdown' or 'json')

    Returns:
        Formatted string
    """
    if format_type == "json":
        return format_json(result)
    else:  # markdown
        return format_markdown(result)


def format_markdown(result: BrainstormResult) -> str:
    """
    Format brainstorm result as markdown.

    Args:
        result: The brainstorm result

    Returns:
        Markdown formatted string
    """
    lines = []
    lines.append("# Brainstorm Results\n")
    lines.append(f"**Seed Prompt:** {result.seed_prompt}\n")
    lines.append(f"**Ideas Generated:** {len(result.ideas)}\n")

    if result.metadata:
        lines.append("\n## Metadata\n")
        for key, value in result.metadata.items():
            if key != "count":  # Already shown above
                lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")

    lines.append("\n---\n")

    for idx, idea in enumerate(result.ideas, 1):
        lines.append(f"\n## {idx}. {idea.name}\n")
        lines.append(f"*{idea.tagline}*\n")

        lines.append("\n### Core Loop\n")
        for step in idea.core_loop:
            lines.append(f"- {step}")

        lines.append("\n### Key Systems\n")
        for system in idea.key_systems:
            lines.append(f"- {system}")

        lines.append(f"\n### Unique Twist\n{idea.unique_twist}\n")

        lines.append(f"\n### Technical Challenge\n{idea.technical_challenge}\n")

        lines.append(f"\n### Feasibility: {idea.feasibility.upper()}\n")
        lines.append(f"**Estimated Scope:** {idea.estimated_scope}\n")

        lines.append(f"\n### Why It Exists\n{idea.why_it_exists}\n")

        if idea.potential_failures:
            lines.append("\n### Potential Failure Modes\n")
            for failure in idea.potential_failures:
                lines.append(f"- {failure}")

        lines.append("\n---\n")

    return "\n".join(lines)


def format_json(result: BrainstormResult) -> str:
    """
    Format brainstorm result as JSON.

    Args:
        result: The brainstorm result

    Returns:
        JSON formatted string
    """
    return json.dumps(
        {
            "seed_prompt": result.seed_prompt,
            "ideas": [idea.model_dump() for idea in result.ideas],
            "metadata": result.metadata,
        },
        indent=2,
        ensure_ascii=False,
    )

