"""Presence/absence matrix for comparing expected vs actual systems."""

import json
from typing import Optional

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.schemas.analysis import (
    CodebaseStructure,
    ExpectedSystems,
    ProjectIntent,
    SystemExpectation,
    SystemGap,
    SystemHoles,
)


class PresenceMatrix:
    """Compares expected systems against actual codebase to find gaps."""

    def __init__(self, llm_client: Optional[LLMClientBase] = None):
        """
        Initialize presence matrix analyzer.

        Args:
            llm_client: Optional LLM client for evidence searching (if None, uses heuristic search)
        """
        self.llm_client = llm_client

    def analyze(
        self,
        structure: CodebaseStructure,
        expected: ExpectedSystems,
        intent: ProjectIntent,
    ) -> SystemHoles:
        """
        Analyze codebase to find missing and partial systems.

        Args:
            structure: CodebaseStructure from scanner
            expected: ExpectedSystems from generator

        Returns:
            SystemHoles with missing, partial, and present systems
        """
        missing: list[SystemGap] = []
        partial: list[SystemGap] = []
        present: list[str] = []

        # Create a searchable structure
        structure_dict = structure.model_dump()
        
        # Combine all searchable text
        searchable_content = {
            "modules": " ".join(structure.modules),
            "entry_points": " ".join(structure.entry_points),
            "public_apis": " ".join(
                " ".join(apis) for apis in structure.public_apis.values()
            ),
            "data_models": " ".join(structure.data_models),
            "config_files": " ".join(structure.config_files),
        }
        searchable_text = " ".join(searchable_content.values()).lower()

        # System category to search patterns mapping
        category_patterns = {
            "lifecycle": ["init", "initialize", "startup", "teardown", "shutdown", "cleanup", "setup"],
            "persistence": ["save", "load", "store", "database", "sql", "json", "yaml", "pickle", "persist"],
            "error_handling": ["error", "exception", "try", "except", "catch", "failure", "recover"],
            "observability": ["log", "monitor", "debug", "trace", "metric", "telemetry"],
            "performance": ["cache", "optimize", "profile", "benchmark", "performance"],
            "tooling": ["build", "deploy", "script", "tool", "cli"],
            "testing": ["test", "pytest", "unittest", "fixture", "mock"],
            "extensibility": ["plugin", "extension", "config", "modular", "hook"],
            "safety": ["validate", "check", "constraint", "security", "sanitize"],
        }

        for system_expectation in expected.systems:
            system_name_lower = system_expectation.name.lower()
            category = system_expectation.category.lower()

            # Get search patterns for this category
            patterns = category_patterns.get(category, [system_name_lower])
            patterns.append(system_name_lower)

            # Search for evidence
            evidence_found = []
            for pattern in patterns:
                if pattern in searchable_text:
                    evidence_found.append(pattern)

            # Check structure flags
            if category == "persistence" and structure.persistence:
                evidence_found.append("persistence_detected")
            if category == "tooling" and structure.has_cli:
                evidence_found.append("cli_detected")
            if category == "testing" and structure.tests:
                evidence_found.append("tests_detected")

            # Determine presence
            if len(evidence_found) >= 2:
                # Multiple pieces of evidence - likely present
                present.append(system_expectation.name)
            elif len(evidence_found) == 1:
                # Some evidence - partial
                partial.append(
                    SystemGap(
                        system=system_expectation.name,
                        category=system_expectation.category,
                        priority=system_expectation.priority,
                        rationale=system_expectation.rationale,
                        evidence_searched=patterns,
                    )
                )
            else:
                # No evidence - missing
                missing.append(
                    SystemGap(
                        system=system_expectation.name,
                        category=system_expectation.category,
                        priority=system_expectation.priority,
                        rationale=system_expectation.rationale,
                        evidence_searched=patterns,
                    )
                )

        return SystemHoles(missing=missing, partial=partial, present=present)

    def _assess_confidence(
        self,
        system_expectation: "SystemExpectation",
        structure: CodebaseStructure,
        intent: ProjectIntent,
        evidence_found: list[str],
    ) -> tuple[str, bool]:
        """
        Assess confidence that a missing system is actually missing vs intentional.

        Args:
            system_expectation: The expected system
            structure: Codebase structure
            intent: Project intent
            evidence_found: Evidence found (empty list for missing)

        Returns:
            Tuple of (confidence_level, may_be_intentional)
        """
        # If project is minimal or foundational, many "missing" systems may be intentional
        if intent.is_minimal:
            # For minimal projects, executable systems are likely intentional omissions
            executable_categories = {
                "lifecycle",
                "observability",
                "performance",
                "testing",
            }
            if system_expectation.category in executable_categories:
                return "low", True

            # Entry points, CLI, API are definitely intentional for base images/templates
            if system_expectation.category == "tooling" and intent.intent_type in (
                "base_image",
                "template",
                "scaffold",
            ):
                return "low", True

        # If no source code exists, most systems are N/A, not missing
        if not structure.has_source_code and system_expectation.category != "tooling":
            return "low", True

        # If no entrypoint and system requires execution, likely intentional
        if not structure.has_entrypoint and intent.intent_type in (
            "base_image",
            "runtime_environment",
        ):
            if system_expectation.category in ("lifecycle", "error_handling"):
                return "low", True

        # High confidence for missing systems in executable utilities
        if intent.intent_type == "executable_utility" and structure.has_source_code:
            if len(evidence_found) == 0:
                return "high", False

        # Medium confidence by default
        return "medium", False

