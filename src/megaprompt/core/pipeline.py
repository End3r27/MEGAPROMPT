"""Main pipeline orchestrator."""

from pathlib import Path
from typing import Optional

from megaprompt.assembler.prompt_assembler import PromptAssembler
from megaprompt.core.cache import Cache
from megaprompt.core.checkpoint import Checkpoint, CheckpointManager
from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.progress import ProgressIndicator
from megaprompt.core.provider_factory import create_client
from megaprompt.schemas.assembly import MegaPrompt
from megaprompt.schemas.constraints import Constraints
from megaprompt.schemas.decomposition import ProjectDecomposition
from megaprompt.schemas.domain import DomainExpansion
from megaprompt.schemas.intent import IntentExtraction
from megaprompt.schemas.risk import RiskAnalysis
from megaprompt.stages.constraint_enforcer import ConstraintEnforcer
from megaprompt.stages.domain_expander import DomainExpander
from megaprompt.stages.intent_extractor import IntentExtractor
from megaprompt.stages.project_decomposer import ProjectDecomposer
from megaprompt.stages.risk_analyzer import RiskAnalyzer


class MegaPromptPipeline:
    """Orchestrates the 5-stage pipeline to generate mega-prompts."""

    def __init__(
        self,
        provider: str = "auto",
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        seed: Optional[int] = None,
        api_key: Optional[str] = None,
        checkpoint_dir: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        use_cache: bool = True,
    ):
        """
        Initialize pipeline.

        Args:
            provider: LLM provider ("ollama", "qwen", "gemini", or "auto")
            base_url: Base URL (provider-specific, not used for Gemini)
            model: Model name (provider-specific, uses defaults if None)
            temperature: Generation temperature (0.0 for determinism)
            seed: Random seed for determinism
            api_key: API key (for Qwen or Gemini)
            checkpoint_dir: Directory for checkpoints (None to disable)
            cache_dir: Directory for cache (None to disable)
            use_cache: Whether to use caching
        """
        self.provider = provider
        self.model = model
        self.llm_client: LLMClientBase = create_client(
            provider=provider,
            model=model,
            temperature=temperature,
            seed=seed,
            base_url=base_url,
            api_key=api_key,
        )

        # Initialize stages
        self.intent_extractor = IntentExtractor(self.llm_client)
        self.project_decomposer = ProjectDecomposer(self.llm_client)
        self.domain_expander = DomainExpander(self.llm_client)
        self.risk_analyzer = RiskAnalyzer(self.llm_client)
        self.constraint_enforcer = ConstraintEnforcer(self.llm_client)

        # Initialize assembler
        self.assembler = PromptAssembler()

        # Initialize checkpoint and cache managers
        self.checkpoint_manager: Optional[CheckpointManager] = None
        if checkpoint_dir:
            self.checkpoint_manager = CheckpointManager(checkpoint_dir)

        self.cache: Optional[Cache] = None
        if use_cache and cache_dir:
            self.cache = Cache(cache_dir)

        # Initialize progress indicator
        self.progress = ProgressIndicator(enabled=True)

    def generate(
        self,
        user_prompt: str,
        verbose: bool = False,
        resume: bool = False,
    ) -> tuple[str, dict]:
        """
        Generate mega-prompt from user input.

        Args:
            user_prompt: Raw user prompt text
            verbose: If True, return intermediate outputs
            resume: If True, attempt to resume from checkpoint

        Returns:
            Tuple of (formatted_mega_prompt_text, intermediate_outputs_dict)

        Raises:
            ValueError: If any stage fails validation
            RuntimeError: If LLM calls fail
        """
        intermediate_outputs = {}
        intent = None
        decomposition = None
        expansion = None
        risk_analysis = None
        constraints = None

            # Try to resume from checkpoint
        if resume and self.checkpoint_manager:
            checkpoint = self.checkpoint_manager.find_latest_checkpoint(user_prompt)
            if checkpoint:
                if verbose:
                    self.progress.update(f"Resuming from checkpoint: {checkpoint.stage} (from {checkpoint.timestamp})")
                intent = checkpoint.intent
                decomposition = checkpoint.decomposition
                expansion = checkpoint.expansion
                risk_analysis = checkpoint.risk_analysis
                constraints = checkpoint.constraints

        try:
            # Stage 1: Intent Extraction
            if intent is None:
                if verbose:
                    self.progress.start_stage("1", "Extracting intent")
                    # Set initial progress for stage 1 (0-20%)
                    self.progress.update("Starting...", progress=0.0)

                # Check cache
                if self.cache:
                    cache_key = self.cache.get_cache_key("intent", user_prompt, self.provider, self.model)
                    cached = self.cache.get(cache_key)
                    if cached:
                        if verbose:
                            self.progress.update("Using cached result (use --no-cache to regenerate)", progress=0.2)
                        intent = IntentExtraction.model_validate(cached)
                    else:
                        if verbose:
                            self.progress.update("Calling LLM...", progress=0.05)
                            # Start gradual progress updates during LLM call (5% to 15% of total)
                            self.progress.start_progress_updates(0.05, 0.15, duration=60.0)
                        intent = self.intent_extractor.extract(user_prompt)
                        if verbose:
                            self.progress.update("Caching result...", progress=0.18)
                        self.cache.set(cache_key, intent.model_dump())
                else:
                    if verbose:
                        self.progress.update("Calling LLM...", progress=0.05)
                        # Start gradual progress updates during LLM call (5% to 15% of total)
                        self.progress.start_progress_updates(0.05, 0.15, duration=60.0)
                    intent = self.intent_extractor.extract(user_prompt)

                # Save checkpoint
                if self.checkpoint_manager:
                    if verbose:
                        self.progress.update("Saving checkpoint...", progress=0.19)
                    self.checkpoint_manager.create_checkpoint(
                        user_prompt, "intent", intent=intent
                    )

            if verbose:
                intermediate_outputs["intent"] = intent.model_dump()
                self.progress.complete_stage(f"Extracted: {intent.project_type} - {intent.core_goal}", progress=0.2)

            # Stage 2: Project Decomposition
            if decomposition is None:
                if verbose:
                    self.progress.start_stage("2", "Decomposing project into systems")
                    # Set progress for stage 2 (20-40%)
                    self.progress.update("Starting...", progress=0.2)

                # Check cache
                if self.cache:
                    cache_key = self.cache.get_cache_key("decomposition", intent.model_dump(), self.provider, self.model)
                    cached = self.cache.get(cache_key)
                    if cached:
                        if verbose:
                            self.progress.update("Using cached result", progress=0.22)
                        decomposition = ProjectDecomposition.model_validate(cached)
                    else:
                        if verbose:
                            self.progress.update("Calling LLM...", progress=0.22)
                            # Start gradual progress updates during LLM call (22% to 35% of total)
                            self.progress.start_progress_updates(0.22, 0.35, duration=60.0)
                        decomposition = self.project_decomposer.decompose(intent)
                        if verbose:
                            self.progress.update("Caching result...", progress=0.38)
                        self.cache.set(cache_key, decomposition.model_dump())
                else:
                    if verbose:
                        self.progress.update("Calling LLM...", progress=0.22)
                        # Start gradual progress updates during LLM call (22% to 35% of total)
                        self.progress.start_progress_updates(0.22, 0.35, duration=60.0)
                    decomposition = self.project_decomposer.decompose(intent)

                # Save checkpoint
                if self.checkpoint_manager:
                    if verbose:
                        self.progress.update("Saving checkpoint...", progress=0.39)
                    self.checkpoint_manager.create_checkpoint(
                        user_prompt, "decomposition", intent=intent, decomposition=decomposition
                    )

            if verbose:
                intermediate_outputs["decomposition"] = decomposition.model_dump()
                self.progress.complete_stage(f"Systems: {len(decomposition.systems)} systems identified", progress=0.4)

            # Stage 3: Domain Expansion
            if expansion is None:
                if verbose:
                    self.progress.start_stage("3", "Expanding system details")
                    # Set progress for stage 3 (40-60%)
                    self.progress.update("Starting...", progress=0.4)

                # Check cache
                if self.cache:
                    cache_key = self.cache.get_cache_key(
                        "expansion", {"intent": intent.model_dump(), "decomposition": decomposition.model_dump()},
                        self.provider, self.model
                    )
                    cached = self.cache.get(cache_key)
                    if cached:
                        if verbose:
                            self.progress.update("Using cached result", progress=0.42)
                        expansion = DomainExpansion.model_validate(cached)
                    else:
                        if verbose:
                            self.progress.update("Calling LLM...", progress=0.42)
                            # Start gradual progress updates during LLM call (42% to 55% of total)
                            self.progress.start_progress_updates(0.42, 0.55, duration=60.0)
                        expansion = self.domain_expander.expand(intent, decomposition)
                        if verbose:
                            self.progress.update("Caching result...", progress=0.58)
                        self.cache.set(cache_key, expansion.model_dump())
                else:
                    if verbose:
                        self.progress.update("Calling LLM...", progress=0.42)
                        # Start gradual progress updates during LLM call (42% to 55% of total)
                        self.progress.start_progress_updates(0.42, 0.55, duration=60.0)
                    expansion = self.domain_expander.expand(intent, decomposition)

                # Save checkpoint
                if self.checkpoint_manager:
                    if verbose:
                        self.progress.update("Saving checkpoint...", progress=0.59)
                    self.checkpoint_manager.create_checkpoint(
                        user_prompt, "expansion", intent=intent, decomposition=decomposition, expansion=expansion
                    )

            if verbose:
                intermediate_outputs["expansion"] = expansion.model_dump()
                self.progress.complete_stage(f"Expanded: {len(expansion.systems)} systems detailed", progress=0.6)

            # Stage 4: Risk Analysis
            if risk_analysis is None:
                if verbose:
                    self.progress.start_stage("4", "Analyzing risks and unknowns")
                    # Set progress for stage 4 (60-80%)
                    self.progress.update("Starting...", progress=0.6)

                # Check cache
                if self.cache:
                    cache_key = self.cache.get_cache_key(
                        "risk_analysis",
                        {
                            "intent": intent.model_dump(),
                            "decomposition": decomposition.model_dump(),
                            "expansion": expansion.model_dump(),
                        },
                        self.provider, self.model
                    )
                    cached = self.cache.get(cache_key)
                    if cached:
                        if verbose:
                            self.progress.update("Using cached result", progress=0.62)
                        risk_analysis = RiskAnalysis.model_validate(cached)
                    else:
                        if verbose:
                            self.progress.update("Calling LLM...", progress=0.62)
                            # Start gradual progress updates during LLM call (62% to 75% of total)
                            self.progress.start_progress_updates(0.62, 0.75, duration=60.0)
                        risk_analysis = self.risk_analyzer.analyze(intent, decomposition, expansion)
                        if verbose:
                            self.progress.update("Caching result...", progress=0.78)
                        self.cache.set(cache_key, risk_analysis.model_dump())
                else:
                    if verbose:
                        self.progress.update("Calling LLM...", progress=0.62)
                        # Start gradual progress updates during LLM call (62% to 75% of total)
                        self.progress.start_progress_updates(0.62, 0.75, duration=60.0)
                    risk_analysis = self.risk_analyzer.analyze(intent, decomposition, expansion)

                # Save checkpoint
                if self.checkpoint_manager:
                    if verbose:
                        self.progress.update("Saving checkpoint...", progress=0.79)
                    self.checkpoint_manager.create_checkpoint(
                        user_prompt, "risk_analysis",
                        intent=intent, decomposition=decomposition, expansion=expansion, risk_analysis=risk_analysis
                    )

            if verbose:
                intermediate_outputs["risk_analysis"] = risk_analysis.model_dump()
                self.progress.complete_stage(
                    f"Risks: {len(risk_analysis.unknowns)} unknowns, "
                    f"{len(risk_analysis.risk_points)} risk points",
                    progress=0.8
                )

            # Stage 5: Constraint Enforcement
            if constraints is None:
                if verbose:
                    self.progress.start_stage("5", "Enforcing constraints")
                    # Set progress for stage 5 (80-90%)
                    self.progress.update("Starting...", progress=0.8)

                # Check cache
                if self.cache:
                    cache_key = self.cache.get_cache_key(
                        "constraints",
                        {
                            "intent": intent.model_dump(),
                            "decomposition": decomposition.model_dump(),
                            "risk_analysis": risk_analysis.model_dump(),
                        },
                        self.provider, self.model
                    )
                    cached = self.cache.get(cache_key)
                    if cached:
                        if verbose:
                            self.progress.update("Using cached result", progress=0.82)
                        constraints = Constraints.model_validate(cached)
                    else:
                        if verbose:
                            self.progress.update("Calling LLM...", progress=0.82)
                            # Start gradual progress updates during LLM call (82% to 87% of total)
                            self.progress.start_progress_updates(0.82, 0.87, duration=60.0)
                        constraints = self.constraint_enforcer.enforce(intent, decomposition, risk_analysis)
                        if verbose:
                            self.progress.update("Caching result...", progress=0.88)
                        self.cache.set(cache_key, constraints.model_dump())
                else:
                    if verbose:
                        self.progress.update("Calling LLM...", progress=0.82)
                        # Start gradual progress updates during LLM call (82% to 87% of total)
                        self.progress.start_progress_updates(0.82, 0.87, duration=60.0)
                    constraints = self.constraint_enforcer.enforce(intent, decomposition, risk_analysis)

                # Save checkpoint
                if self.checkpoint_manager:
                    if verbose:
                        self.progress.update("Saving checkpoint...", progress=0.89)
                    self.checkpoint_manager.create_checkpoint(
                        user_prompt, "constraints",
                        intent=intent, decomposition=decomposition, expansion=expansion,
                        risk_analysis=risk_analysis, constraints=constraints
                    )

            if verbose:
                intermediate_outputs["constraints"] = constraints.model_dump()
                self.progress.complete_stage(f"Constraints: {constraints.language or 'None'} / {constraints.engine or 'None'}", progress=0.9)

            # Assembly: Generate final mega-prompt
            if verbose:
                self.progress.start_stage("6", "Assembling final mega-prompt")
                self.progress.update("Combining all stages...", progress=0.95)
            mega_prompt_text = self.assembler.assemble_text(
                intent, decomposition, expansion, risk_analysis, constraints
            )

            if verbose:
                intermediate_outputs["final"] = {"status": "success"}
                self.progress.complete_stage("Mega-prompt assembled", progress=1.0)
                self.progress.finish()

            return mega_prompt_text, intermediate_outputs

        except Exception as e:
            # Save checkpoint with error
            if self.checkpoint_manager:
                error_msg = f"{type(e).__name__}: {str(e)}"
                self.checkpoint_manager.create_checkpoint(
                    user_prompt, "error",
                    intent=intent, decomposition=decomposition, expansion=expansion,
                    risk_analysis=risk_analysis, constraints=constraints, error=error_msg
                )

            # Provide better error context
            stage_name = "unknown"
            if intent is None:
                stage_name = "Intent Extraction (Stage 1)"
            elif decomposition is None:
                stage_name = "Project Decomposition (Stage 2)"
            elif expansion is None:
                stage_name = "Domain Expansion (Stage 3)"
            elif risk_analysis is None:
                stage_name = "Risk Analysis (Stage 4)"
            elif constraints is None:
                stage_name = "Constraint Enforcement (Stage 5)"
            else:
                stage_name = "Assembly"

            error_context = f"\n\nError occurred during: {stage_name}"
            error_context += f"\nProvider: {self.provider}"
            if self.model:
                error_context += f"\nModel: {self.model}"

            if isinstance(e, ValueError) and "Validation failed" in str(e):
                error_context += "\n\nThis is a validation error. The LLM response didn't match the expected schema."
                error_context += "\nTry running again, or check the error details above for suggestions."

            if verbose:
                intermediate_outputs["error"] = str(e)
                intermediate_outputs["error_context"] = error_context

            raise RuntimeError(f"{str(e)}{error_context}") from e

