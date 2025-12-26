"""Constraint enforcement stage implementation."""

import json
from pathlib import Path

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.validator import validate_schema
from megaprompt.schemas.constraints import Constraints
from megaprompt.schemas.decomposition import ProjectDecomposition
from megaprompt.schemas.intent import IntentExtraction
from megaprompt.schemas.risk import RiskAnalysis


class ConstraintEnforcer:
    """Enforces technical constraints on the project."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize constraint enforcer.

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
            / "constraint_enforcement.txt"
        )
        return template_path.read_text(encoding="utf-8")

    def enforce(
        self,
        intent: IntentExtraction,
        decomposition: ProjectDecomposition,
        risk_analysis: RiskAnalysis,
    ) -> Constraints:
        """
        Enforce technical constraints.

        Args:
            intent: Extracted intent
            decomposition: Decomposed systems
            risk_analysis: Risk analysis results

        Returns:
            Validated Constraints model

        Raises:
            ValueError: If enforcement or validation fails
        """
        # Format template
        prompt = self.prompt_template.format(
            project_type=intent.project_type,
            core_goal=intent.core_goal,
            systems=json.dumps(decomposition.systems),
            risk_points=json.dumps(risk_analysis.risk_points),
        )

        # Call LLM
        response = self.llm_client.generate(prompt)

        # Extract JSON
        json_data = self.llm_client.extract_json(response)

        # Validate and return
        return validate_schema(json_data, Constraints)

