"""Idea synthesis stage implementation."""

import json
from pathlib import Path

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.validator import validate_schema
from megaprompt.schemas.brainstorm import ConceptCluster, ProjectIdea


class IdeaSynthesizer:
    """Synthesizes structured project ideas from concept clusters."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize idea synthesizer.

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
            / "idea_synthesis.txt"
        )
        return template_path.read_text(encoding="utf-8")

    def synthesize(
        self,
        cluster: ConceptCluster,
        constraints: list[str] | None = None,
        domain: str | None = None,
        depth: str = "medium",
    ) -> ProjectIdea:
        """
        Synthesize a structured project idea from a cluster.

        Args:
            cluster: The concept cluster to generate idea from
            constraints: Optional list of constraints (e.g., ['local-ai', 'offline'])
            domain: Optional domain bias
            depth: Depth level ('low', 'medium', 'high')

        Returns:
            Validated ProjectIdea model

        Raises:
            ValueError: If synthesis or validation fails
        """
        # Build constraints context
        constraints_context = ""
        if constraints:
            constraints_list = ", ".join(constraints)
            constraints_context = f"\n\nCONSTRAINTS: The idea must respect these constraints: {constraints_list}"

        # Build domain context
        domain_context = ""
        if domain:
            domain_context = f"\n\nDOMAIN BIAS: Focus on {domain} domain concepts."

        # Build depth requirement
        depth_requirements = {
            "low": "Focus on high-level concepts and core mechanics.",
            "medium": "Provide moderate detail on systems and mechanics.",
            "high": "Include detailed system specifications and technical considerations.",
        }
        depth_requirement = f"\n\nDEPTH REQUIREMENT: {depth_requirements.get(depth, depth_requirements['medium'])}"

        # Format template
        prompt = self.prompt_template.format(
            cluster_name=cluster.name,
            cluster_description=cluster.description,
            axis_combination=json.dumps(cluster.axis_combination),
            constraints_context=constraints_context,
            domain_context=domain_context,
            depth_requirement=depth_requirement,
        )

        # Call LLM
        response = self.llm_client.generate(prompt)

        # Extract JSON
        json_data = self.llm_client.extract_json(response)

        # Validate and return (with retry on validation failure)
        try:
            return validate_schema(
                json_data,
                ProjectIdea,
                llm_client=self.llm_client,
                original_prompt=prompt,
                max_retries=1,
            )
        except ValueError:
            # If retry also fails, re-raise with original error
            return validate_schema(json_data, ProjectIdea)

