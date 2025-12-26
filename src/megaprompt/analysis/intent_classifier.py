"""Project intent classifier stage implementation."""

import json
from pathlib import Path
from typing import Optional

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.validator import validate_schema
from megaprompt.schemas.analysis import CodebaseStructure, ProjectIntent


class IntentClassifier:
    """Classifies the intent of a project before system hole analysis."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize intent classifier.

        Args:
            llm_client: LLM client for API calls
        """
        self.llm_client = llm_client
        self.prompt_template = self._load_template()

    def _load_template(self) -> str:
        """Load prompt template from file."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "prompts"
            / "project_intent_classification.txt"
        )
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        else:
            return self._default_template()

    def _default_template(self) -> str:
        """Default template if file doesn't exist."""
        return """You are classifying the intent/purpose of a codebase project.

Given the following structural information, determine what kind of project this is.

Codebase Structure:
{codebase_structure}

Heuristic Observations:
{heuristics}

Possible intent types:
- executable_utility: Standalone executable tool/service
- base_image: Docker base image or foundational layer
- runtime_environment: Runtime environment setup
- build_image: Build/CI image with toolchains
- library_image: Library or dependency container
- template: Template/scaffold project
- scaffold: Starter template
- library: Reusable library code
- unknown: Cannot determine with confidence

Return a JSON object with:
{{
  "intent_type": "one of the intent types above",
  "confidence": "high, medium, or low",
  "reasoning": "Explanation of why this intent was chosen, referencing heuristics",
  "is_minimal": true/false,
  "maturity_level": "foundation, template, prototype, production, or unknown"
}}

Focus on heuristics first. If the project appears intentionally minimal (base image, template, etc.), mark is_minimal as true.
"""

    def classify(self, structure: CodebaseStructure) -> ProjectIntent:
        """
        Classify project intent using heuristics first, then AI.

        Args:
            structure: CodebaseStructure from scanner

        Returns:
            Validated ProjectIntent model
        """
        # First, run heuristics
        heuristics = self._run_heuristics(structure)

        # Convert structure to JSON string for prompt
        structure_json = json.dumps(structure.model_dump(), indent=2)
        heuristics_json = json.dumps(heuristics, indent=2)

        # Format template
        prompt = self.prompt_template.format(
            codebase_structure=structure_json,
            heuristics=heuristics_json,
        )

        # Call LLM
        response = self.llm_client.generate(prompt)

        # Extract JSON
        json_data = self.llm_client.extract_json(response)

        # Validate and return
        try:
            return validate_schema(
                json_data,
                ProjectIntent,
                llm_client=self.llm_client,
                original_prompt=prompt,
                max_retries=1,
            )
        except ValueError:
            return validate_schema(json_data, ProjectIntent)

    def _run_heuristics(self, structure: CodebaseStructure) -> dict:
        """
        Run heuristic checks to inform intent classification.

        Args:
            structure: CodebaseStructure

        Returns:
            Dictionary of heuristic observations
        """
        heuristics = {
            "observations": [],
            "likely_intent": None,
            "confidence": "medium",
        }

        # Check for executable indicators
        has_executable_code = (
            len(structure.modules) > 0
            or len(structure.entry_points) > 0
            or structure.has_cli
            or structure.has_api
        )

        # Check for minimalism indicators
        is_very_minimal = (
            structure.file_count == 0
            or (structure.file_count < 5 and len(structure.config_files) == structure.file_count)
        )

        # Docker-specific heuristics
        if structure.has_docker:
            if not structure.has_entrypoint:
                heuristics["observations"].append(
                    "Dockerfile present but no ENTRYPOINT/CMD - may be base image"
                )
            if not has_executable_code:
                heuristics["observations"].append(
                    "Dockerfile present but no executable code detected"
                )

        # Minimal codebase heuristics
        if is_very_minimal:
            heuristics["observations"].append(
                "Very minimal codebase - likely base image, template, or scaffold"
            )
            heuristics["likely_intent"] = "base_image" if structure.has_docker else "template"
            heuristics["confidence"] = "high"

        # Executable utility indicators
        if has_executable_code and structure.has_entrypoint:
            heuristics["observations"].append("Executable code and entrypoint detected")
            heuristics["likely_intent"] = "executable_utility"
            heuristics["confidence"] = "high"
        elif has_executable_code and not structure.has_docker:
            heuristics["observations"].append(
                "Executable code detected but no containerization"
            )
            heuristics["likely_intent"] = "executable_utility"
            heuristics["confidence"] = "medium"

        # Template/scaffold indicators
        if structure.has_readme and is_very_minimal:
            heuristics["observations"].append("README present with minimal code - may be template")
            if not heuristics["likely_intent"]:
                heuristics["likely_intent"] = "template"
                heuristics["confidence"] = "medium"

        # Library indicators
        if (
            len(structure.modules) > 0
            and not structure.has_cli
            and not structure.has_api
            and not structure.has_entrypoint
        ):
            heuristics["observations"].append("Code present but no entry points - may be library")
            if not heuristics["likely_intent"]:
                heuristics["likely_intent"] = "library"
                heuristics["confidence"] = "medium"

        return heuristics

