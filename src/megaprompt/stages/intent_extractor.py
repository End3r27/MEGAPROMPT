"""Intent extraction stage implementation."""

from pathlib import Path

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.validator import validate_schema
from megaprompt.schemas.intent import IntentExtraction


class IntentExtractor:
    """Extracts core intent from user prompt."""

    def __init__(self, llm_client: LLMClientBase):
        """
        Initialize intent extractor.

        Args:
            llm_client: LLM client for API calls
        """
        self.llm_client = llm_client
        self.prompt_template = self._load_template()

    def _load_template(self) -> str:
        """Load prompt template from file."""
        template_path = Path(__file__).parent.parent.parent.parent / "prompts" / "intent_extraction.txt"
        return template_path.read_text(encoding="utf-8")

    def extract(self, user_prompt: str) -> IntentExtraction:
        """
        Extract intent from user prompt.

        Args:
            user_prompt: Raw user prompt text

        Returns:
            Validated IntentExtraction model

        Raises:
            ValueError: If extraction or validation fails
        """
        # Format template
        prompt = self.prompt_template.format(user_prompt=user_prompt)

        # Call LLM
        response = self.llm_client.generate(prompt)

        # Extract JSON
        json_data = self.llm_client.extract_json(response)

        # Validate and return (with retry on validation failure)
        try:
            return validate_schema(
                json_data,
                IntentExtraction,
                llm_client=self.llm_client,
                original_prompt=prompt,
                max_retries=1,
            )
        except ValueError:
            # If retry also fails, re-raise with original error
            return validate_schema(json_data, IntentExtraction)

