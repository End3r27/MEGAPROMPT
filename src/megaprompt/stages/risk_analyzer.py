"""Risk analysis stage implementation."""

import json
from pathlib import Path

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.validator import validate_schema
from megaprompt.schemas.decomposition import ProjectDecomposition
from megaprompt.schemas.domain import DomainExpansion
from megaprompt.schemas.intent import IntentExtraction
from megaprompt.schemas.risk import RiskAnalysis


class RiskAnalyzer:
    """Analyzes project for unknowns and risks."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize risk analyzer.

        Args:
            llm_client: LLM client for API calls
        """
        self.llm_client = llm_client
        self.prompt_template = self._load_template()

    def _load_template(self) -> str:
        """Load prompt template from file."""
        template_path = Path(__file__).parent.parent.parent.parent / "prompts" / "risk_analysis.txt"
        return template_path.read_text(encoding="utf-8")

    def analyze(
        self,
        intent: IntentExtraction,
        decomposition: ProjectDecomposition,
        expansion: DomainExpansion,
    ) -> RiskAnalysis:
        """
        Analyze project for unknowns and risks.

        Args:
            intent: Extracted intent
            decomposition: Decomposed systems
            expansion: Expanded system details

        Returns:
            Validated RiskAnalysis model

        Raises:
            ValueError: If analysis or validation fails
        """
        # Format template - convert expansion to a readable format
        systems_str = json.dumps(decomposition.systems)
        system_details_str = json.dumps(
            {k: v.model_dump() for k, v in expansion.systems.items()},
            indent=2,
        )

        prompt = self.prompt_template.format(
            project_type=intent.project_type,
            core_goal=intent.core_goal,
            systems=systems_str,
            system_details=system_details_str,
        )

        # Call LLM
        response = self.llm_client.generate(prompt)

        # Extract JSON
        json_data = self.llm_client.extract_json(response)

        # Validate and return (with retry on validation failure)
        try:
            return validate_schema(
                json_data,
                RiskAnalysis,
                llm_client=self.llm_client,
                original_prompt=prompt,
                max_retries=1,
            )
        except ValueError:
            # If retry also fails, re-raise with original error
            return validate_schema(json_data, RiskAnalysis)

