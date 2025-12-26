"""Architectural inference stage implementation."""

import json
from pathlib import Path

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.validator import validate_schema
from megaprompt.schemas.analysis import ArchitecturalInference, CodebaseStructure


class ArchitecturalInferrer:
    """Infers architectural patterns and project type from codebase structure."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize architectural inferrer.

        Args:
            llm_client: LLM client for API calls
        """
        self.llm_client = llm_client
        self.prompt_template = self._load_template()

    def _load_template(self) -> str:
        """Load prompt template from file."""
        template_path = (
            Path(__file__).parent.parent.parent.parent / "prompts" / "architectural_inference.txt"
        )
        return template_path.read_text(encoding="utf-8")

    def infer(self, structure: CodebaseStructure) -> ArchitecturalInference:
        """
        Infer architectural information from codebase structure.

        Args:
            structure: CodebaseStructure extracted from scanning

        Returns:
            Validated ArchitecturalInference model
        """
        # Convert structure to JSON string for prompt
        structure_json = json.dumps(structure.model_dump(), indent=2)

        # Format template
        prompt = self.prompt_template.format(codebase_structure=structure_json)

        # Call LLM
        response = self.llm_client.generate(prompt)

        # Extract JSON
        json_data = self.llm_client.extract_json(response)

        # Validate and return
        try:
            return validate_schema(
                json_data,
                ArchitecturalInference,
                llm_client=self.llm_client,
                original_prompt=prompt,
                max_retries=1,
            )
        except ValueError:
            return validate_schema(json_data, ArchitecturalInference)

