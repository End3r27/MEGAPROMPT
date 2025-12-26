"""Main pipeline orchestrator."""

from typing import Optional

from megaprompt.assembler.prompt_assembler import PromptAssembler
from megaprompt.core.llm_base import LLMClientBase
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
        """
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

    def generate(self, user_prompt: str, verbose: bool = False) -> tuple[str, dict]:
        """
        Generate mega-prompt from user input.

        Args:
            user_prompt: Raw user prompt text
            verbose: If True, return intermediate outputs

        Returns:
            Tuple of (formatted_mega_prompt_text, intermediate_outputs_dict)

        Raises:
            ValueError: If any stage fails validation
            RuntimeError: If LLM calls fail
        """
        intermediate_outputs = {}

        try:
            # Stage 1: Intent Extraction
            if verbose:
                print("Stage 1: Extracting intent...", flush=True)
            intent = self.intent_extractor.extract(user_prompt)
            if verbose:
                intermediate_outputs["intent"] = intent.model_dump()
                print(f"  Extracted: {intent.project_type} - {intent.core_goal}")

            # Stage 2: Project Decomposition
            if verbose:
                print("Stage 2: Decomposing project into systems...", flush=True)
            decomposition = self.project_decomposer.decompose(intent)
            if verbose:
                intermediate_outputs["decomposition"] = decomposition.model_dump()
                print(f"  Systems: {len(decomposition.systems)} systems identified")

            # Stage 3: Domain Expansion
            if verbose:
                print("Stage 3: Expanding system details...", flush=True)
            expansion = self.domain_expander.expand(intent, decomposition)
            if verbose:
                intermediate_outputs["expansion"] = expansion.model_dump()
                print(f"  Expanded: {len(expansion.systems)} systems detailed")

            # Stage 4: Risk Analysis
            if verbose:
                print("Stage 4: Analyzing risks and unknowns...", flush=True)
            risk_analysis = self.risk_analyzer.analyze(
                intent, decomposition, expansion
            )
            if verbose:
                intermediate_outputs["risk_analysis"] = risk_analysis.model_dump()
                print(
                    f"  Risks: {len(risk_analysis.unknowns)} unknowns, "
                    f"{len(risk_analysis.risk_points)} risk points"
                )

            # Stage 5: Constraint Enforcement
            if verbose:
                print("Stage 5: Enforcing constraints...", flush=True)
            constraints = self.constraint_enforcer.enforce(
                intent, decomposition, risk_analysis
            )
            if verbose:
                intermediate_outputs["constraints"] = constraints.model_dump()
                print(f"  Constraints: {constraints.language or 'None'} / {constraints.engine or 'None'}")

            # Assembly: Generate final mega-prompt
            if verbose:
                print("Assembling final mega-prompt...", flush=True)
            mega_prompt_text = self.assembler.assemble_text(
                intent, decomposition, expansion, risk_analysis, constraints
            )

            if verbose:
                intermediate_outputs["final"] = {"status": "success"}

            return mega_prompt_text, intermediate_outputs

        except Exception as e:
            if verbose:
                intermediate_outputs["error"] = str(e)
            raise

