"""Domain expansion stage implementation."""

import json
from pathlib import Path

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.validator import validate_schema
from megaprompt.schemas.decomposition import ProjectDecomposition
from megaprompt.schemas.domain import DomainExpansion
from megaprompt.schemas.intent import IntentExtraction


class DomainExpander:
    """Expands systems with detailed specifications."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize domain expander.

        Args:
            llm_client: LLM client for API calls
        """
        self.llm_client = llm_client
        self.prompt_template = self._load_template()

    def _load_template(self) -> str:
        """Load prompt template from file."""
        template_path = Path(__file__).parent.parent.parent.parent / "prompts" / "domain_expansion.txt"
        return template_path.read_text(encoding="utf-8")

    def expand(
        self, intent: IntentExtraction, decomposition: ProjectDecomposition
    ) -> DomainExpansion:
        """
        Expand systems with detailed specifications.

        Args:
            intent: Extracted intent
            decomposition: Decomposed systems

        Returns:
            Validated DomainExpansion model

        Raises:
            ValueError: If expansion or validation fails
        """
        # Format template
        prompt = self.prompt_template.format(
            project_type=intent.project_type,
            core_goal=intent.core_goal,
            systems=json.dumps(decomposition.systems),
        )

        # Call LLM
        response = self.llm_client.generate(prompt)

        # Extract JSON
        json_data = self.llm_client.extract_json(response)

        # Validate and return
        return validate_schema(json_data, DomainExpansion)

