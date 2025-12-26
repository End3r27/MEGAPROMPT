"""Unit tests for Pydantic schemas."""

import pytest

from megaprompt.schemas.constraints import Constraints
from megaprompt.schemas.decomposition import ProjectDecomposition
from megaprompt.schemas.domain import DomainExpansion, SystemDetails
from megaprompt.schemas.intent import IntentExtraction
from megaprompt.schemas.risk import RiskAnalysis


class TestIntentExtraction:
    """Test IntentExtraction schema."""

    def test_valid_intent(self):
        """Test valid intent extraction."""
        intent = IntentExtraction(
            project_type="simulation game",
            core_goal="Build a civilization simulator",
            user_expectations=["emergent behavior", "AI NPCs"],
            non_goals=["multiplayer"],
        )
        assert intent.project_type == "simulation game"
        assert len(intent.user_expectations) == 2
        assert len(intent.non_goals) == 1

    def test_minimal_intent(self):
        """Test intent with minimal fields."""
        intent = IntentExtraction(
            project_type="web app",
            core_goal="Build a todo app",
        )
        assert intent.user_expectations == []
        assert intent.non_goals == []


class TestProjectDecomposition:
    """Test ProjectDecomposition schema."""

    def test_valid_decomposition(self):
        """Test valid project decomposition."""
        decomp = ProjectDecomposition(
            systems=["Agent AI", "World Simulation", "Economy"]
        )
        assert len(decomp.systems) == 3
        assert "Agent AI" in decomp.systems

    def test_empty_systems(self):
        """Test that systems list can be empty (though not recommended)."""
        decomp = ProjectDecomposition(systems=[])
        assert decomp.systems == []

    def test_systems_with_objects(self):
        """Test that systems can be objects with 'name' field (normalized to strings)."""
        decomp = ProjectDecomposition(
            systems=[
                "System1",
                {"name": "System2", "description": "Some description"},
                {"name": "System3"},
            ]
        )
        assert len(decomp.systems) == 3
        assert "System1" in decomp.systems
        assert "System2" in decomp.systems
        assert "System3" in decomp.systems
        assert all(isinstance(s, str) for s in decomp.systems)


class TestDomainExpansion:
    """Test DomainExpansion schema."""

    def test_valid_expansion(self):
        """Test valid domain expansion."""
        expansion = DomainExpansion(
            systems={
                "Agent AI": SystemDetails(
                    responsibilities=["Make decisions", "Learn"],
                    inputs=["world state", "events"],
                    outputs=["actions", "decisions"],
                    failure_modes=["Timeout", "Invalid state"],
                    dependencies=["World Simulation"],
                )
            }
        )
        assert "Agent AI" in expansion.systems
        assert len(expansion.systems["Agent AI"].responsibilities) == 2


class TestRiskAnalysis:
    """Test RiskAnalysis schema."""

    def test_valid_risk_analysis(self):
        """Test valid risk analysis."""
        risk = RiskAnalysis(
            unknowns=["How agents discover technologies"],
            risk_points=["Performance with many agents"],
        )
        assert len(risk.unknowns) == 1
        assert len(risk.risk_points) == 1


class TestConstraints:
    """Test Constraints schema."""

    def test_valid_constraints(self):
        """Test valid constraints."""
        constraints = Constraints(
            engine="Godot",
            language="GDScript",
            ai_execution="local only",
            determinism=True,
            performance_limits=["Handle 1000+ agents"],
        )
        assert constraints.engine == "Godot"
        assert constraints.determinism is True

    def test_minimal_constraints(self):
        """Test constraints with defaults."""
        constraints = Constraints()
        assert constraints.ai_execution == "local only"
        assert constraints.determinism is True

