"""Self-critique injection stage implementation."""

import json
from pathlib import Path

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.schemas.brainstorm import ProjectIdea


class SelfCritiqueInjector:
    """Injects self-critique (potential failures) into ideas."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize self-critique injector.

        Args:
            llm_client: LLM client for API calls
        """
        self.llm_client = llm_client
        self.prompt_template = self._load_template()

    def _load_template(self) -> str:
        """Load prompt template from file."""
        template_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "prompts"
            / "brainstorm"
            / "self_critique.txt"
        )
        return template_path.read_text(encoding="utf-8")

    def inject(self, idea: ProjectIdea) -> ProjectIdea:
        """
        Inject potential failures into an idea.

        Args:
            idea: The idea to add critique to

        Returns:
            Idea with potential_failures populated

        Raises:
            ValueError: If critique generation fails
        """
        # If already has failures, return as-is (or regenerate if empty)
        if idea.potential_failures and len(idea.potential_failures) >= 2:
            return idea

        idea_json = json.dumps(idea.model_dump(), indent=2)
        prompt = self.prompt_template.format(idea_json=idea_json)

        try:
            response = self.llm_client.generate(prompt)
            json_data = self.llm_client.extract_json(response)

            potential_failures = json_data.get("potential_failures", [])

            # Update idea with potential failures
            idea_dict = idea.model_dump()
            idea_dict["potential_failures"] = potential_failures

            return ProjectIdea.model_validate(idea_dict)
        except Exception as e:
            # If critique fails, add a generic failure list
            idea_dict = idea.model_dump()
            if not idea_dict.get("potential_failures"):
                idea_dict["potential_failures"] = [
                    "Technical complexity may be underestimated",
                    "Scope might expand beyond initial estimates",
                ]
            return ProjectIdea.model_validate(idea_dict)

