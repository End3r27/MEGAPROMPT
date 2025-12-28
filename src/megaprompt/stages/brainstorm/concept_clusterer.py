"""Concept clustering stage implementation."""

import json
from pathlib import Path

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.validator import validate_schema
from megaprompt.schemas.brainstorm import ConceptClusters, IdeaSpaceExpansion


class ConceptClusterer:
    """Groups concept axes into idea clusters."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize concept clusterer.

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
            / "concept_clustering.txt"
        )
        return template_path.read_text(encoding="utf-8")

    def cluster(
        self, idea_space: IdeaSpaceExpansion, target_count: int, domain: str | None = None
    ) -> ConceptClusters:
        """
        Cluster concept axes into idea buckets.

        Args:
            idea_space: The expanded idea space with axes
            target_count: Target number of ideas to generate
            domain: Optional domain bias

        Returns:
            Validated ConceptClusters model

        Raises:
            ValueError: If clustering or validation fails
        """
        # Build domain context if provided
        domain_context = ""
        if domain:
            domain_context = f"\n\nDOMAIN BIAS: Focus on {domain} domain concepts."

        # Calculate approximate number of clusters (target_count / 2-3)
        num_clusters = max(2, target_count // 2)
        count_requirement = f"\n\nGenerate approximately {num_clusters} clusters to eventually produce around {target_count} ideas."

        # Format template
        prompt = self.prompt_template.format(
            axes=json.dumps(idea_space.axes),
            rationale=idea_space.rationale,
            domain_context=domain_context,
            count_requirement=count_requirement,
        )

        # Call LLM
        response = self.llm_client.generate(prompt)

        # Extract JSON
        json_data = self.llm_client.extract_json(response)

        # Validate and return (with retry on validation failure)
        try:
            return validate_schema(
                json_data,
                ConceptClusters,
                llm_client=self.llm_client,
                original_prompt=prompt,
                max_retries=1,
            )
        except ValueError:
            # If retry also fails, re-raise with original error
            return validate_schema(json_data, ConceptClusters)

