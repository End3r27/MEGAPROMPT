"""Expected systems generator stage implementation."""

import json
from pathlib import Path

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.validator import validate_schema
from megaprompt.schemas.analysis import (
    ArchitecturalInference,
    ExpectedSystems,
    ProjectIntent,
)


class ExpectedSystemsGenerator:
    """Generates canonical system checklist based on project type and intent."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize expected systems generator.

        Args:
            llm_client: LLM client for API calls
        """
        self.llm_client = llm_client
        self.prompt_template = self._load_template()

    def _load_template(self) -> str:
        """Load prompt template from file."""
        template_path = (
            Path(__file__).parent.parent.parent.parent / "prompts" / "expected_systems.txt"
        )
        return template_path.read_text(encoding="utf-8")

    def generate(
        self, inference: ArchitecturalInference, intent: ProjectIntent
    ) -> ExpectedSystems:
        """
        Generate expected systems for the project type and intent.

        Args:
            inference: ArchitecturalInference from previous stage
            intent: ProjectIntent from intent classifier

        Returns:
            Validated ExpectedSystems model
        """
        # Format template
        prompt = self.prompt_template.format(
            project_type=inference.project_type,
            patterns=", ".join(inference.dominant_patterns),
            architectural_style=inference.architectural_style,
            intent_type=intent.intent_type,
            is_minimal=str(intent.is_minimal).lower(),
            maturity_level=intent.maturity_level,
        )

        # Call LLM
        response = self.llm_client.generate(prompt)

        # Extract JSON
        json_data = self.llm_client.extract_json(response)

        # Validate and return
        try:
            return validate_schema(
                json_data,
                ExpectedSystems,
                llm_client=self.llm_client,
                original_prompt=prompt,
                max_retries=1,
            )
        except ValueError:
            return validate_schema(json_data, ExpectedSystems)

