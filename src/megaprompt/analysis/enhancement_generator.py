"""Enhancement generator stage implementation."""

import json
from pathlib import Path

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.validator import validate_schema
from megaprompt.schemas.analysis import (
    ArchitecturalInference,
    CodebaseStructure,
    Enhancements,
    SystemHoles,
)


class EnhancementGenerator:
    """Generates context-aware enhancement suggestions."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize enhancement generator.

        Args:
            llm_client: LLM client for API calls
        """
        self.llm_client = llm_client
        self.prompt_template = self._load_template()

    def _load_template(self) -> str:
        """Load prompt template from file."""
        template_path = (
            Path(__file__).parent.parent.parent.parent / "prompts" / "enhancement_generation.txt"
        )
        return template_path.read_text(encoding="utf-8")

    def generate(
        self,
        structure: CodebaseStructure,
        inference: ArchitecturalInference,
        holes: SystemHoles,
    ) -> Enhancements:
        """
        Generate enhancement suggestions.

        Args:
            structure: CodebaseStructure from scanner
            inference: ArchitecturalInference from inference stage
            holes: SystemHoles from presence matrix

        Returns:
            Validated Enhancements model
        """
        # Convert to JSON strings for prompt
        structure_json = json.dumps(structure.model_dump(), indent=2)
        inference_json = json.dumps(inference.model_dump(), indent=2)
        holes_json = json.dumps(
            {
                "missing": [h.model_dump() for h in holes.missing],
                "partial": [h.model_dump() for h in holes.partial],
                "present": holes.present,
            },
            indent=2,
        )

        # Format template
        prompt = self.prompt_template.format(
            codebase_structure=structure_json,
            architecture=inference_json,
            system_holes=holes_json,
        )

        # Call LLM
        response = self.llm_client.generate(prompt)

        # Extract JSON
        json_data = self.llm_client.extract_json(response)

        # Validate and return
        try:
            return validate_schema(
                json_data,
                Enhancements,
                llm_client=self.llm_client,
                original_prompt=prompt,
                max_retries=1,
            )
        except ValueError:
            return validate_schema(json_data, Enhancements)

