"""Brainstorm pipeline orchestrator."""

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.logging import get_logger, StructuredLogger
from megaprompt.core.progress import ProgressIndicator
from megaprompt.core.provider_factory import create_client
from megaprompt.schemas.brainstorm import (
    BrainstormResult,
    ConceptClusters,
    IdeaSpaceExpansion,
    ProjectIdea,
)
from megaprompt.stages.brainstorm.concept_clusterer import ConceptClusterer
from megaprompt.stages.brainstorm.deduplicator import Deduplicator
from megaprompt.stages.brainstorm.idea_space_expander import IdeaSpaceExpander
from megaprompt.stages.brainstorm.idea_synthesizer import IdeaSynthesizer
from megaprompt.stages.brainstorm.quality_enforcer import QualityEnforcer
from megaprompt.stages.brainstorm.self_critique_injector import SelfCritiqueInjector


class BrainstormPipeline:
    """Orchestrates the brainstorm pipeline to generate multiple project ideas."""

    def __init__(
        self,
        provider: str = "auto",
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,  # Higher temperature for creativity
        seed: Optional[int] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize brainstorm pipeline.

        Args:
            provider: LLM provider ("ollama", "qwen", "gemini", "openrouter", or "auto")
            base_url: Base URL (provider-specific, not used for Gemini)
            model: Model name (provider-specific, uses defaults if None)
            temperature: Generation temperature (higher for more creativity)
            seed: Random seed for determinism
            api_key: API key (for Qwen, Gemini, or OpenRouter)
        """
        self.provider = provider
        self.model = model

        # Create base client
        base_client = create_client(
            provider=provider,
            model=model,
            temperature=temperature,
            seed=seed,
            base_url=base_url,
            api_key=api_key,
        )

        # Wrap client with logging (cost tracking optional for brainstorm)
        from megaprompt.core.llm_wrapper import wrap_client_with_logging

        actual_model = model or "default"
        self.llm_client: LLMClientBase = wrap_client_with_logging(
            client=base_client,
            provider=provider,
            model=actual_model,
            track_costs=False,  # Can enable if needed
        )

        # Initialize stages
        self.idea_space_expander = IdeaSpaceExpander(self.llm_client)
        self.concept_clusterer = ConceptClusterer(self.llm_client)
        self.idea_synthesizer = IdeaSynthesizer(self.llm_client)
        self.quality_enforcer = QualityEnforcer(self.llm_client)
        self.deduplicator = Deduplicator(similarity_threshold=0.7)
        self.self_critique_injector = SelfCritiqueInjector(self.llm_client)

        # Initialize progress indicator
        self.progress = ProgressIndicator(enabled=True)

        # Initialize logger
        self.logger: StructuredLogger = get_logger("megaprompt.brainstorm")

    def brainstorm(
        self,
        seed_prompt: str,
        count: int = 8,
        domain: Optional[str] = None,
        depth: str = "medium",
        diversity: str = "medium",
        constraints: Optional[list[str]] = None,
        verbose: bool = False,
    ) -> BrainstormResult:
        """
        Generate multiple project ideas from a seed prompt.

        Args:
            seed_prompt: The original vague prompt
            count: Target number of ideas to generate
            domain: Optional domain bias (e.g., 'gamedev', 'web', 'ai')
            depth: Depth level ('low', 'medium', 'high')
            diversity: Diversity level ('low', 'medium', 'high') - affects similarity threshold
            constraints: Optional list of constraints (e.g., ['local-ai', 'offline'])
            verbose: If True, log progress

        Returns:
            BrainstormResult with ideas and metadata

        Raises:
            ValueError: If any stage fails validation
            RuntimeError: If generation fails
        """
        start_time = time.time()

        if verbose:
            self.progress.update(f"Starting brainstorm for: {seed_prompt[:50]}...")

        try:
            # Stage 1: Idea Space Expansion
            if verbose:
                self.progress.update("Expanding idea space...", progress=0.1)
            idea_space: IdeaSpaceExpansion = self.idea_space_expander.expand(
                seed_prompt, domain=domain
            )

            # Stage 2: Concept Clustering
            if verbose:
                self.progress.update("Clustering concepts...", progress=0.2)
            clusters: ConceptClusters = self.concept_clusterer.cluster(
                idea_space, target_count=count, domain=domain
            )

            # Stage 3: Idea Synthesis (generate ideas per cluster)
            if verbose:
                self.progress.update(
                    f"Generating ideas from {len(clusters.clusters)} clusters...",
                    progress=0.3,
                )

            # Calculate ideas per cluster (distribute evenly, with remainder)
            ideas_per_cluster = max(1, count // len(clusters.clusters))
            extra_ideas = count % len(clusters.clusters)

            all_ideas: list[ProjectIdea] = []

            # Generate ideas in parallel per cluster
            with ThreadPoolExecutor(max_workers=min(4, len(clusters.clusters))) as executor:
                futures = {}
                total_submitted = 0
                for idx, cluster in enumerate(clusters.clusters):
                    # Distribute extra ideas to first clusters
                    cluster_idea_count = ideas_per_cluster + (1 if idx < extra_ideas else 0)
                    for _ in range(cluster_idea_count):
                        future = executor.submit(
                            self._generate_single_idea,
                            cluster,
                            constraints,
                            domain,
                            depth,
                        )
                        futures[future] = cluster.name
                        total_submitted += 1

                completed = 0
                for future in as_completed(futures):
                    completed += 1
                    try:
                        idea = future.result()
                        all_ideas.append(idea)
                        if verbose:
                            self.progress.update(
                                f"Generated idea {completed}/{total_submitted}",
                                progress=0.3 + (0.4 * completed / max(total_submitted, 1)),
                            )
                    except Exception as e:
                        self.logger.warning(f"Failed to generate idea from cluster: {e}")

            # Stage 4: Quality Enforcement
            if verbose:
                self.progress.update("Enforcing quality gates...", progress=0.7)
            quality_checked_ideas: list[ProjectIdea] = []
            for idea in all_ideas:
                status, checked_idea, reason = self.quality_enforcer.enforce(idea)
                if status == "accepted":
                    quality_checked_ideas.append(checked_idea)
                elif status == "improved" and checked_idea:
                    quality_checked_ideas.append(checked_idea)
                # Skip rejected ideas

            # Stage 5: Deduplication
            if verbose:
                self.progress.update("Deduplicating ideas...", progress=0.8)

            # Adjust similarity threshold based on diversity setting
            similarity_thresholds = {"low": 0.9, "medium": 0.7, "high": 0.5}
            self.deduplicator.similarity_threshold = similarity_thresholds.get(
                diversity, 0.7
            )

            unique_ideas = self.deduplicator.deduplicate(quality_checked_ideas)

            # If we don't have enough ideas, generate more
            while len(unique_ideas) < count and len(unique_ideas) < count * 1.5:
                # Pick a random cluster and generate another idea
                cluster = random.choice(clusters.clusters)
                try:
                    idea = self._generate_single_idea(
                        cluster, constraints, domain, depth
                    )
                    status, checked_idea, _ = self.quality_enforcer.enforce(idea)
                    if status in ("accepted", "improved") and checked_idea:
                        unique_ideas.append(checked_idea)
                        unique_ideas = self.deduplicator.deduplicate(unique_ideas)
                        if verbose:
                            self.progress.update(
                                f"Generated additional idea: {len(unique_ideas)}/{count}",
                                progress=0.85,
                            )
                except Exception:
                    pass

                if len(unique_ideas) >= count * 2:  # Safety limit
                    break

            # Limit to count
            unique_ideas = unique_ideas[:count]

            # Stage 6: Self-Critique Injection
            if verbose:
                self.progress.update("Adding self-critique...", progress=0.9)

            final_ideas: list[ProjectIdea] = []
            for idea in unique_ideas:
                try:
                    critiqued_idea = self.self_critique_injector.inject(idea)
                    final_ideas.append(critiqued_idea)
                except Exception:
                    # If critique fails, use original idea
                    final_ideas.append(idea)

            elapsed_time = time.time() - start_time

            # Create result
            result = BrainstormResult(
                seed_prompt=seed_prompt,
                ideas=final_ideas,
                metadata={
                    "count": len(final_ideas),
                    "target_count": count,
                    "clusters_used": len(clusters.clusters),
                    "generation_time": elapsed_time,
                    "domain": domain,
                    "depth": depth,
                    "diversity": diversity,
                },
            )

            if verbose:
                self.progress.update(
                    f"Brainstorm complete: {len(final_ideas)} ideas generated",
                    progress=1.0,
                )

            return result

        except Exception as e:
            self.logger.error(f"Brainstorm pipeline failed: {e}", exc_info=True)
            raise RuntimeError(f"Brainstorm failed: {e}") from e

    def _generate_single_idea(
        self,
        cluster,
        constraints: Optional[list[str]],
        domain: Optional[str],
        depth: str,
    ) -> ProjectIdea:
        """Generate a single idea from a cluster (helper method)."""
        return self.idea_synthesizer.synthesize(
            cluster, constraints=constraints, domain=domain, depth=depth
        )

