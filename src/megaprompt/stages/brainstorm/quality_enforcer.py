"""Quality enforcement stage implementation."""

import json
from pathlib import Path
from typing import Literal

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.schemas.brainstorm import ProjectIdea


class QualityEnforcer:
    """Enforces quality gates on project ideas."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize quality enforcer.

        Args:
            llm_client: LLM client for API calls (optional, can be algorithmic)
        """
        self.llm_client = llm_client
        self.prompt_template = self._load_template()

    def _load_template(self) -> str:
        """Load prompt template from file."""
        template_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "prompts"
            / "brainstorm"
            / "quality_enforcement.txt"
        )
        return template_path.read_text(encoding="utf-8")

    def enforce(self, idea: ProjectIdea) -> tuple[Literal["accepted", "rejected", "improved"], ProjectIdea | None, str | None]:
        """
        Enforce quality gates on an idea.

        Args:
            idea: The project idea to validate

        Returns:
            Tuple of (status, idea_or_none, reason_or_none)
            - status: "accepted", "rejected", or "improved"
            - idea_or_none: The idea if accepted/improved, None if rejected
            - reason_or_none: Rejection reason if rejected, improvement notes if improved
        """
        # First, do algorithmic checks
        if self._algorithmic_check(idea) == "rejected":
            return "rejected", None, "Failed algorithmic quality checks (missing core_loop, unbounded scope, etc.)"

        # Use LLM for more nuanced validation
        idea_json = json.dumps(idea.model_dump(), indent=2)
        prompt = self.prompt_template.format(idea_json=idea_json)

        try:
            response = self.llm_client.generate(prompt)
            json_data = self.llm_client.extract_json(response)

            status = json_data.get("status", "accepted")
            
            if status == "rejected":
                return "rejected", None, json_data.get("reason", "Quality check failed")
            elif status == "improved":
                # Merge improvements into idea
                improvements = json_data.get("improvements", {})
                idea_dict = idea.model_dump()
                idea_dict.update(improvements)
                improved_idea = ProjectIdea.model_validate(idea_dict)
                return "improved", improved_idea, "Improvements applied"
            else:  # accepted
                return "accepted", idea, None
        except Exception:
            # If LLM check fails, fall back to algorithmic check result
            return "accepted", idea, None

    def _algorithmic_check(self, idea: ProjectIdea) -> Literal["accepted", "rejected"]:
        """
        Perform algorithmic quality checks.

        Args:
            idea: The idea to check

        Returns:
            "accepted" or "rejected"
        """
        # Check for missing core_loop
        if not idea.core_loop or len(idea.core_loop) < 2:
            return "rejected"

        # Check for missing key_systems
        if not idea.key_systems or len(idea.key_systems) < 2:
            return "rejected"

        # Check for unbounded scope keywords
        unbounded_keywords = ["everything", "all", "complete", "universal", "infinite"]
        idea_text = (
            idea.name + " " + idea.tagline + " " + idea.unique_twist
        ).lower()
        if any(keyword in idea_text for keyword in unbounded_keywords):
            # Allow if it's clearly bounded by context
            if "simulator" in idea_text and "everything" in idea_text:
                return "rejected"

        # Check for vague placeholder text
        vague_phrases = ["placeholder", "todo", "tbd", "to be determined"]
        if any(phrase in idea_text for phrase in vague_phrases):
            return "rejected"

        return "accepted"

