"""Analysis pipeline orchestrator."""

from pathlib import Path
from typing import Optional

from megaprompt.analysis.enhancement_generator import EnhancementGenerator
from megaprompt.analysis.inference import ArchitecturalInferrer
from megaprompt.analysis.intent_drift import IntentDriftDetector
from megaprompt.analysis.presence_matrix import PresenceMatrix
from megaprompt.analysis.scanner import CodebaseScanner
from megaprompt.analysis.system_generator import ExpectedSystemsGenerator
from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.progress import ProgressIndicator
from megaprompt.schemas.analysis import AnalysisReport


class AnalysisPipeline:
    """Orchestrates the analysis pipeline to generate codebase analysis reports."""

    def __init__(
        self,
        llm_client: LLMClientBase,
        depth: str = "high",
        verbose: bool = False,
    ):
        """
        Initialize analysis pipeline.

        Args:
            llm_client: LLM client for AI stages
            depth: Scanning depth: "low", "medium", "high"
            verbose: Whether to show progress
        """
        self.llm_client = llm_client
        self.depth = depth
        self.verbose = verbose

        # Initialize stages
        self.scanner = CodebaseScanner(depth=depth)
        self.inferrer = ArchitecturalInferrer(llm_client)
        self.system_generator = ExpectedSystemsGenerator(llm_client)
        self.presence_matrix = PresenceMatrix(llm_client=None)  # No LLM for heuristic search
        self.enhancement_generator = EnhancementGenerator(llm_client)
        self.intent_drift_detector = IntentDriftDetector(llm_client)

        # Initialize progress indicator
        self.progress = ProgressIndicator(enabled=verbose)

    def analyze(
        self,
        codebase_path: str | Path,
        original_prompt_path: Optional[str | Path] = None,
    ) -> AnalysisReport:
        """
        Analyze codebase and generate report.

        Args:
            codebase_path: Path to codebase directory
            original_prompt_path: Optional path to original design prompt (for intent drift)

        Returns:
            AnalysisReport with all analysis results
        """
        if self.verbose:
            self.progress.start_stage("1", "Scanning codebase structure")

        # Stage 1: Static scan
        structure = self.scanner.scan(codebase_path)

        if self.verbose:
            self.progress.complete_stage(
                f"Found {len(structure.modules)} modules, {len(structure.entry_points)} entry points",
                progress=0.2,
            )
            self.progress.start_stage("2", "Inferring architecture")

        # Stage 2: Architectural inference
        inference = self.inferrer.infer(structure)

        if self.verbose:
            self.progress.complete_stage(
                f"Project type: {inference.project_type}",
                progress=0.4,
            )
            self.progress.start_stage("3", "Generating expected systems")

        # Stage 3: Expected systems generation
        expected = self.system_generator.generate(inference)

        if self.verbose:
            self.progress.complete_stage(
                f"Generated {len(expected.systems)} expected systems",
                progress=0.6,
            )
            self.progress.start_stage("4", "Analyzing presence/absence")

        # Stage 4: Presence/absence analysis
        holes = self.presence_matrix.analyze(structure, expected)

        if self.verbose:
            self.progress.complete_stage(
                f"Found {len(holes.missing)} missing, {len(holes.partial)} partial systems",
                progress=0.75,
            )
            self.progress.start_stage("5", "Generating enhancements")

        # Stage 5: Enhancement generation
        enhancements = self.enhancement_generator.generate(structure, inference, holes)

        if self.verbose:
            self.progress.complete_stage(
                f"Generated {len(enhancements.enhancements)} enhancement suggestions",
                progress=0.9,
            )

        # Stage 6: Intent drift (optional)
        intent_drift = None
        if original_prompt_path:
            if self.verbose:
                self.progress.start_stage("6", "Detecting intent drift")
            intent_drift = self.intent_drift_detector.detect(structure, original_prompt_path)
            if self.verbose:
                self.progress.complete_stage(
                    f"Found {len(intent_drift.drifts)} drift items",
                    progress=0.95,
                )

        if self.verbose:
            self.progress.complete_stage("Analysis complete", progress=1.0)
            self.progress.finish()

        return AnalysisReport(
            structure=structure,
            inference=inference,
            holes=holes,
            enhancements=enhancements,
            intent_drift=intent_drift,
        )

