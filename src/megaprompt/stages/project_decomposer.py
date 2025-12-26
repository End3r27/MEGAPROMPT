"""Project decomposition stage implementation."""

import json
from pathlib import Path

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.validator import validate_schema
from megaprompt.schemas.decomposition import ProjectDecomposition
from megaprompt.schemas.intent import IntentExtraction


class ProjectDecomposer:
    """Decomposes project into orthogonal systems."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize project decomposer.

        Args:
            llm_client: LLM client for API calls
        """
        self.llm_client = llm_client
        self.prompt_template = self._load_template()

    def _load_template(self) -> str:
        """Load prompt template from file."""
        template_path = Path(__file__).parent.parent.parent.parent / "prompts" / "project_decomposition.txt"
        return template_path.read_text(encoding="utf-8")

    def decompose(self, intent: IntentExtraction) -> ProjectDecomposition:
        """
        Decompose project into systems.

        Args:
            intent: Extracted intent from previous stage

        Returns:
            Validated ProjectDecomposition model

        Raises:
            ValueError: If decomposition or validation fails
        """
        # Format template
        prompt = self.prompt_template.format(
            project_type=intent.project_type,
            core_goal=intent.core_goal,
            user_expectations=json.dumps(intent.user_expectations),
        )

        # Call LLM
        response = self.llm_client.generate(prompt)

        # Extract JSON
        json_data = self.llm_client.extract_json(response)

        # Validate and return
        return validate_schema(json_data, ProjectDecomposition)

