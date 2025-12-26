"""Mega-prompt assembly from stage outputs."""

from pathlib import Path

from megaprompt.schemas.assembly import MegaPrompt
from megaprompt.schemas.constraints import Constraints
from megaprompt.schemas.decomposition import ProjectDecomposition
from megaprompt.schemas.domain import DomainExpansion
from megaprompt.schemas.intent import IntentExtraction
from megaprompt.schemas.risk import RiskAnalysis


class PromptAssembler:
    """Assembles final mega-prompt from all stage outputs."""

    def __init__(self):
        """Initialize prompt assembler."""
        self.template = self._load_template()

    def _load_template(self) -> str:
        """Load mega-prompt template from file."""
        template_path = (
            Path(__file__).parent.parent.parent.parent / "templates" / "mega_prompt_template.md"
        )
        return template_path.read_text(encoding="utf-8")

    def assemble(
        self,
        intent: IntentExtraction,
        decomposition: ProjectDecomposition,
        expansion: DomainExpansion,
        risk_analysis: RiskAnalysis,
        constraints: Constraints,
    ) -> MegaPrompt:
        """
        Assemble final mega-prompt from all stage outputs.

        Args:
            intent: Extracted intent
            decomposition: Decomposed systems
            expansion: Expanded system details
            risk_analysis: Risk analysis results
            constraints: Technical constraints

        Returns:
            Complete MegaPrompt model
        """
        # Build system role
        system_role = self._build_system_role(intent, constraints)

        # Build project overview
        project_overview = self._build_project_overview(intent)

        # Build core requirements
        core_requirements = self._build_core_requirements(intent)

        # Build system architecture
        system_architecture = self._build_system_architecture(
            decomposition, expansion
        )

        # Build AI design rules
        ai_design_rules = self._build_ai_design_rules(constraints)

        # Build unknown areas
        unknown_areas = self._build_unknown_areas(risk_analysis)

        # Build deliverables
        deliverables = self._build_deliverables(decomposition, constraints)

        # Build response format
        response_format = self._build_response_format()

        # Create formatted mega-prompt text
        formatted_text = self.template.format(
            system_role=system_role,
            project_overview=project_overview,
            core_requirements=core_requirements,
            system_architecture=system_architecture,
            ai_design_rules=ai_design_rules,
            unknown_areas=unknown_areas,
            deliverables=deliverables,
            response_format=response_format,
        )

        # Return as MegaPrompt model
        return MegaPrompt(
            system_role=system_role,
            project_overview=project_overview,
            core_requirements=core_requirements.split("\n") if core_requirements else [],
            system_architecture={},
            ai_design_rules=ai_design_rules.split("\n") if ai_design_rules else [],
            unknown_areas=unknown_areas.split("\n") if unknown_areas else [],
            deliverables={},
            response_format=response_format.split("\n") if response_format else [],
        )

    def assemble_text(
        self,
        intent: IntentExtraction,
        decomposition: ProjectDecomposition,
        expansion: DomainExpansion,
        risk_analysis: RiskAnalysis,
        constraints: Constraints,
    ) -> str:
        """
        Assemble final mega-prompt as formatted text.

        Args:
            intent: Extracted intent
            decomposition: Decomposed systems
            expansion: Expanded system details
            risk_analysis: Risk analysis results
            constraints: Technical constraints

        Returns:
            Formatted mega-prompt text
        """
        # Build all sections
        system_role = self._build_system_role(intent, constraints)
        project_overview = self._build_project_overview(intent)
        core_requirements = self._build_core_requirements(intent)
        system_architecture = self._build_system_architecture(
            decomposition, expansion
        )
        ai_design_rules = self._build_ai_design_rules(constraints)
        unknown_areas = self._build_unknown_areas(risk_analysis)
        deliverables = self._build_deliverables(decomposition, constraints)
        response_format = self._build_response_format()

        # Format template
        return self.template.format(
            system_role=system_role,
            project_overview=project_overview,
            core_requirements=core_requirements,
            system_architecture=system_architecture,
            ai_design_rules=ai_design_rules,
            unknown_areas=unknown_areas,
            deliverables=deliverables,
            response_format=response_format,
        )

    def _build_system_role(
        self, intent: IntentExtraction, constraints: Constraints
    ) -> str:
        """Build system role section."""
        role_parts = [
            f"You are a senior {intent.project_type.replace('_', ' ')} engineer and AI architect."
        ]

        if constraints.language:
            role_parts.append(f"Expert in {constraints.language}.")

        if constraints.engine:
            role_parts.append(f"Specialist in {constraints.engine}.")

        role_parts.append(
            "Your task is to implement the following project specification with precision, clarity, and attention to detail."
        )

        return " ".join(role_parts)

    def _build_project_overview(self, intent: IntentExtraction) -> str:
        """Build project overview section."""
        overview = intent.core_goal

        if intent.user_expectations:
            overview += "\n\nKey expectations:\n"
            for exp in intent.user_expectations:
                overview += f"- {exp}\n"

        if intent.non_goals:
            overview += "\nNon-goals (explicitly out of scope):\n"
            for non_goal in intent.non_goals:
                overview += f"- {non_goal}\n"

        return overview

    def _build_core_requirements(self, intent: IntentExtraction) -> str:
        """Build core requirements section."""
        requirements = []

        requirements.append(intent.core_goal)

        for exp in intent.user_expectations:
            requirements.append(f"- {exp}")

        return "\n".join(requirements)

    def _build_system_architecture(
        self, decomposition: ProjectDecomposition, expansion: DomainExpansion
    ) -> str:
        """Build system architecture section."""
        arch = ""

        for system_name in decomposition.systems:
            if system_name not in expansion.systems:
                continue

            details = expansion.systems[system_name]
            arch += f"\n## {system_name}\n\n"

            arch += "**Responsibilities:**\n"
            for resp in details.responsibilities:
                arch += f"- {resp}\n"

            arch += "\n**Inputs:**\n"
            for inp in details.inputs:
                arch += f"- {inp}\n"

            arch += "\n**Outputs:**\n"
            for out in details.outputs:
                arch += f"- {out}\n"

            arch += "\n**Failure Modes:**\n"
            for failure in details.failure_modes:
                arch += f"- {failure}\n"

            arch += "\n**Dependencies:**\n"
            for dep in details.dependencies:
                arch += f"- {dep}\n"

            arch += "\n"

        return arch.strip()

    def _build_ai_design_rules(self, constraints: Constraints) -> str:
        """Build AI design rules section."""
        rules = []

        rules.append("- No magic behavior - all actions must be explainable and traceable")
        rules.append("- All learning must be explainable and deterministic")
        if constraints.determinism:
            rules.append("- System must be fully deterministic (same inputs = same outputs)")
        if constraints.ai_execution == "local only":
            rules.append("- AI execution must be local only - no cloud dependencies")
        if constraints.modularity:
            rules.append(f"- Architecture must be {constraints.modularity}")
        if constraints.performance_limits:
            for limit in constraints.performance_limits:
                rules.append(f"- Performance requirement: {limit}")

        return "\n".join(rules)

    def _build_unknown_areas(self, risk_analysis: RiskAnalysis) -> str:
        """Build unknown areas section."""
        if not risk_analysis.unknowns:
            return "None identified - all areas are sufficiently specified."

        areas = []
        for unknown in risk_analysis.unknowns:
            areas.append(f"- {unknown}")

        return "\n".join(areas)

    def _build_deliverables(
        self, decomposition: ProjectDecomposition, constraints: Constraints
    ) -> str:
        """Build deliverables section."""
        deliverables = []

        deliverables.append("**Folder Structure:**")
        deliverables.append("- Well-organized project structure matching the system architecture")
        deliverables.append("- Separate modules/directories for each major system")

        deliverables.append("\n**Core Classes/Components:**")
        for system in decomposition.systems:
            deliverables.append(f"- {system} implementation")

        deliverables.append("\n**Implementation Details:**")
        if constraints.language:
            deliverables.append(f"- Code in {constraints.language}")
        if constraints.engine:
            deliverables.append(f"- Built for {constraints.engine}")
        deliverables.append("- Complete simulation/application loop")
        deliverables.append("- Error handling and logging")
        deliverables.append("- Documentation for each system")

        return "\n".join(deliverables)

    def _build_response_format(self) -> str:
        """Build response format section."""
        return """- Step-by-step implementation approach
- No skipped logic or placeholders
- Clear explanation of design decisions
- Code structure and organization plan
- Testing strategy
- Implementation timeline (if applicable)"""

