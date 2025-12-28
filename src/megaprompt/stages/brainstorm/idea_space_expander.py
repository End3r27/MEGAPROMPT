"""Idea space expansion stage implementation."""

from pathlib import Path

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.validator import validate_schema
from megaprompt.schemas.brainstorm import IdeaSpaceExpansion


class IdeaSpaceExpander:
    """Expands seed prompt into concept axes for diverse idea generation."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize idea space expander.

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
            / "idea_space_expansion.txt"
        )
        return template_path.read_text(encoding="utf-8")

    def expand(
        self, seed_prompt: str, domain: str | None = None
    ) -> IdeaSpaceExpansion:
        """
        Expand seed prompt into concept axes.

        Args:
            seed_prompt: The original vague prompt
            domain: Optional domain bias (e.g., 'gamedev', 'web', 'ai')

        Returns:
            Validated IdeaSpaceExpansion model

        Raises:
            ValueError: If expansion or validation fails
        """
        # Build domain context if provided
        domain_context = ""
        if domain:
            domain_context = f"\n\nDOMAIN BIAS: Focus on {domain} domain concepts and constraints."

        # Format template
        prompt = self.prompt_template.format(
            seed_prompt=seed_prompt, domain_context=domain_context
        )

        # Call LLM
        response = self.llm_client.generate(prompt)

        # Extract JSON
        json_data = self.llm_client.extract_json(response)

        # Validate and return (with retry on validation failure)
        try:
            return validate_schema(
                json_data,
                IdeaSpaceExpansion,
                llm_client=self.llm_client,
                original_prompt=prompt,
                max_retries=1,
            )
        except ValueError:
            # If retry also fails, re-raise with original error
            return validate_schema(json_data, IdeaSpaceExpansion)

