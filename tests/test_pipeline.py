"""Integration and end-to-end tests for pipeline."""

import json
from unittest.mock import MagicMock, patch

import pytest

from megaprompt.core.llm_client import OllamaClient
from megaprompt.core.pipeline import MegaPromptPipeline
from megaprompt.schemas.constraints import Constraints
from megaprompt.schemas.decomposition import ProjectDecomposition
from megaprompt.schemas.domain import DomainExpansion, SystemDetails
from megaprompt.schemas.intent import IntentExtraction
from megaprompt.schemas.risk import RiskAnalysis


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock(spec=OllamaClient)
    return client


@pytest.fixture
def sample_intent():
    """Sample intent extraction result."""
    return IntentExtraction(
        project_type="simulation game",
        core_goal="Build a civilization simulator with AI NPCs",
        user_expectations=["emergent behavior", "autonomous agents"],
        non_goals=[],
    )


@pytest.fixture
def sample_decomposition():
    """Sample project decomposition result."""
    return ProjectDecomposition(
        systems=["Agent AI", "World Simulation", "Economy", "Social Structures"]
    )


@pytest.fixture
def sample_expansion():
    """Sample domain expansion result."""
    return DomainExpansion(
        systems={
            "Agent AI": SystemDetails(
                responsibilities=["Make decisions", "Learn from experience"],
                inputs=["world state", "events"],
                outputs=["actions", "goals"],
                failure_modes=["Invalid state", "Timeout"],
                dependencies=["World Simulation"],
            ),
            "World Simulation": SystemDetails(
                responsibilities=["Update world state", "Handle physics"],
                inputs=["agent actions"],
                outputs=["world state updates"],
                failure_modes=["State corruption"],
                dependencies=[],
            ),
        }
    )


@pytest.fixture
def sample_risk_analysis():
    """Sample risk analysis result."""
    return RiskAnalysis(
        unknowns=["How agents discover new technologies", "How factions emerge"],
        risk_points=["Performance scaling with many agents", "LLM determinism"],
    )


@pytest.fixture
def sample_constraints():
    """Sample constraints result."""
    return Constraints(
        engine="Godot",
        language="GDScript",
        ai_execution="local only",
        determinism=True,
        performance_limits=["Handle 1000+ agents"],
    )


class TestLLMClient:
    """Test Ollama client."""

    def test_extract_json_from_code_block(self):
        """Test JSON extraction from markdown code block."""
        client = OllamaClient()
        response = '```json\n{"key": "value"}\n```'
        result = client.extract_json(response)
        assert result == {"key": "value"}

    def test_extract_json_direct(self):
        """Test JSON extraction from direct JSON."""
        client = OllamaClient()
        response = '{"key": "value"}'
        result = client.extract_json(response)
        assert result == {"key": "value"}

    def test_extract_json_invalid(self):
        """Test JSON extraction with invalid input."""
        client = OllamaClient()
        response = "This is not JSON"
        with pytest.raises(ValueError):
            client.extract_json(response)


class TestPipelineStages:
    """Test individual pipeline stages with mocked LLM."""

    @patch("megaprompt.stages.intent_extractor.OllamaClient")
    def test_intent_extractor(self, mock_client_class, mock_llm_client, sample_intent):
        """Test intent extraction stage."""
        from megaprompt.stages.intent_extractor import IntentExtractor

        mock_client_class.return_value = mock_llm_client
        mock_llm_client.extract_json.return_value = sample_intent.model_dump()

        extractor = IntentExtractor(mock_llm_client)
        result = extractor.extract("Build a civilization simulator")

        assert result.project_type == sample_intent.project_type
        assert result.core_goal == sample_intent.core_goal

    @patch("megaprompt.stages.project_decomposer.OllamaClient")
    def test_project_decomposer(
        self, mock_client_class, mock_llm_client, sample_intent, sample_decomposition
    ):
        """Test project decomposition stage."""
        from megaprompt.stages.project_decomposer import ProjectDecomposer

        mock_client_class.return_value = mock_llm_client
        mock_llm_client.extract_json.return_value = sample_decomposition.model_dump()

        decomposer = ProjectDecomposer(mock_llm_client)
        result = decomposer.decompose(sample_intent)

        assert len(result.systems) == len(sample_decomposition.systems)


class TestPipelineIntegration:
    """Integration tests for full pipeline with mocked LLM."""

    @patch("megaprompt.core.pipeline.OllamaClient")
    def test_full_pipeline_mock(
        self,
        mock_client_class,
        sample_intent,
        sample_decomposition,
        sample_expansion,
        sample_risk_analysis,
        sample_constraints,
    ):
        """Test full pipeline with all stages mocked."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock responses for each stage
        mock_responses = [
            sample_intent.model_dump(),
            sample_decomposition.model_dump(),
            sample_expansion.model_dump(),
            sample_risk_analysis.model_dump(),
            sample_constraints.model_dump(),
        ]
        mock_client.extract_json.side_effect = mock_responses

        pipeline = MegaPromptPipeline(model="test-model")
        result_text, intermediate = pipeline.generate("Build a civilization simulator", verbose=True)

        # Check that all stages were called
        assert mock_client.generate.call_count == 5

        # Check intermediate outputs
        assert "intent" in intermediate
        assert "decomposition" in intermediate
        assert "expansion" in intermediate
        assert "risk_analysis" in intermediate
        assert "constraints" in intermediate

        # Check result contains expected sections
        assert "SYSTEM ROLE" in result_text
        assert "PROJECT OVERVIEW" in result_text
        assert "CORE REQUIREMENTS" in result_text
        assert "SYSTEM ARCHITECTURE" in result_text

