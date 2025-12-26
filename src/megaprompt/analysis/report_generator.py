"""Report generator for analysis results."""

from pathlib import Path

from megaprompt.schemas.analysis import AnalysisReport


class ReportGenerator:
    """Generates formatted reports from analysis results."""

    def __init__(self):
        """Initialize report generator."""
        self.markdown_template = self._load_markdown_template()

    def _load_markdown_template(self) -> str:
        """Load markdown report template."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "templates"
            / "analysis_report_template.md"
        )
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        else:
            # Return default template if file doesn't exist
            return self._default_template()

    def _default_template(self) -> str:
        """Default markdown template."""
        return """# Codebase Analysis Report

## Project Overview

**Project Type:** {project_type}
**Architectural Style:** {architectural_style}
**Dominant Patterns:** {patterns}

## Critical System Holes

{missing_systems}

## Partial Systems

{partial_systems}

## Present Systems

{present_systems}

## Suggested Enhancements

{enhancements}

## Intent Drift

{intent_drift}

## Codebase Structure

**Modules:** {module_count}
**Entry Points:** {entry_points_count}
**Data Models:** {data_models_count}
**Has Tests:** {has_tests}
**Has Persistence:** {has_persistence}
**Has CLI:** {has_cli}
**Has API:** {has_api}
"""

    def generate_markdown(self, report: AnalysisReport) -> str:
        """
        Generate markdown report.

        Args:
            report: AnalysisReport to format

        Returns:
            Formatted markdown string
        """
        # Format missing systems
        missing_lines = []
        for gap in report.holes.missing:
            priority_icon = "🔴" if gap.priority == "critical" else "🟠" if gap.priority == "high" else "🟡"
            missing_lines.append(
                f"- {priority_icon} **{gap.system}** ({gap.category}, {gap.priority} priority)\n"
                f"  - {gap.rationale}"
            )
        missing_systems_text = "\n".join(missing_lines) if missing_lines else "None identified"

        # Format partial systems
        partial_lines = []
        for gap in report.holes.partial:
            partial_lines.append(
                f"- ⚠️ **{gap.system}** ({gap.category}, {gap.priority} priority)\n"
                f"  - {gap.rationale}\n"
                f"  - Evidence searched: {', '.join(gap.evidence_searched[:5])}"
            )
        partial_systems_text = "\n".join(partial_lines) if partial_lines else "None"

        # Format present systems
        present_systems_text = (
            "\n".join(f"- ✓ {name}" for name in report.holes.present)
            if report.holes.present
            else "None"
        )

        # Format enhancements
        enhancement_lines = []
        for enh in report.enhancements.enhancements:
            effort_icon = "⚡" if enh.effort == "low" else "🔧" if enh.effort == "medium" else "🏗️"
            risk_icon = "✅" if enh.risk == "low" else "⚠️" if enh.risk == "medium" else "🔴"
            fit_icon = "✓" if enh.fits_existing else "✗"
            enhancement_lines.append(
                f"- {effort_icon} **{enh.name}** ({enh.effort} effort, {enh.risk} risk, fits existing: {fit_icon})\n"
                f"  - {enh.description}\n"
                f"  - Why: {enh.why}"
            )
        enhancements_text = "\n".join(enhancement_lines) if enhancement_lines else "None suggested"

        # Format intent drift
        intent_drift_text = "No original intent provided for comparison."
        if report.intent_drift and report.intent_drift.drifts:
            drift_lines = []
            for drift in report.intent_drift.drifts:
                severity_icon = "🔴" if drift.severity == "critical" else "🟠" if drift.severity == "medium" else "🟡"
                drift_lines.append(
                    f"- {severity_icon} **{drift.original_intent}**\n"
                    f"  - Current state: {drift.current_state}\n"
                    f"  - Severity: {drift.severity}"
                )
            intent_drift_text = "\n".join(drift_lines)

        # Format patterns
        patterns_text = ", ".join(report.inference.dominant_patterns) if report.inference.dominant_patterns else "None identified"

        # Generate report using template
        report_text = self.markdown_template.format(
            project_type=report.inference.project_type,
            architectural_style=report.inference.architectural_style or "Not specified",
            patterns=patterns_text,
            missing_systems=missing_systems_text,
            partial_systems=partial_systems_text,
            present_systems=present_systems_text,
            enhancements=enhancements_text,
            intent_drift=intent_drift_text,
            module_count=len(report.structure.modules),
            entry_points_count=len(report.structure.entry_points),
            data_models_count=len(report.structure.data_models),
            has_tests="Yes" if report.structure.tests else "No",
            has_persistence="Yes" if report.structure.persistence else "No",
            has_cli="Yes" if report.structure.has_cli else "No",
            has_api="Yes" if report.structure.has_api else "No",
        )

        return report_text

    def generate_json(self, report: AnalysisReport) -> str:
        """
        Generate JSON report.

        Args:
            report: AnalysisReport to format

        Returns:
            Formatted JSON string
        """
        import json

        return json.dumps(report.model_dump(), indent=2, default=str)

