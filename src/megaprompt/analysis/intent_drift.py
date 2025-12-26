"""Intent drift detection stage implementation."""

import json
from pathlib import Path

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.validator import validate_schema
from megaprompt.schemas.analysis import CodebaseStructure, IntentDrift


class IntentDriftDetector:
    """Detects drift between original design intent and implementation."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize intent drift detector.

        Args:
            llm_client: LLM client for API calls
        """
        self.llm_client = llm_client
        self.prompt_template = self._load_template()

    def _load_template(self) -> str:
        """Load prompt template from file."""
        template_path = (
            Path(__file__).parent.parent.parent.parent / "prompts" / "intent_drift.txt"
        )
        return template_path.read_text(encoding="utf-8")

    def detect(
        self, structure: CodebaseStructure, original_prompt_path: str | Path
    ) -> IntentDrift:
        """
        Detect intent drift between original design and implementation.

        Args:
            structure: CodebaseStructure from scanner
            original_prompt_path: Path to original design prompt/intent file (can be absolute or relative)

        Returns:
            Validated IntentDrift model

        Raises:
            ValueError: If path does not exist or is not a file
            PermissionError: If file cannot be read
        """
        # Resolve path to handle relative paths, ~ expansion, and symlinks
        original_prompt_path = Path(original_prompt_path).expanduser().resolve()
        
        if not original_prompt_path.exists():
            raise ValueError(f"Original prompt path does not exist: {original_prompt_path}")
        
        if not original_prompt_path.is_file():
            raise ValueError(f"Original prompt path is not a file: {original_prompt_path}")
        
        try:
            original_intent = original_prompt_path.read_text(encoding="utf-8")
        except PermissionError as e:
            raise PermissionError(f"Cannot read original prompt file: {original_prompt_path}") from e
        except UnicodeDecodeError as e:
            raise ValueError(f"Cannot decode file as UTF-8: {original_prompt_path}. Please ensure the file is text-encoded.") from e

        # Convert structure to JSON string
        structure_json = json.dumps(structure.model_dump(), indent=2)

        # Format template
        prompt = self.prompt_template.format(
            original_intent=original_intent,
            codebase_structure=structure_json,
        )

        # Call LLM
        response = self.llm_client.generate(prompt)

        # Extract JSON
        json_data = self.llm_client.extract_json(response)

        # Validate and return
        try:
            return validate_schema(
                json_data,
                IntentDrift,
                llm_client=self.llm_client,
                original_prompt=prompt,
                max_retries=1,
            )
        except ValueError:
            return validate_schema(json_data, IntentDrift)

