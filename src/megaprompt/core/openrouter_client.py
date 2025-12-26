"""OpenRouter LLM client wrapper using OpenAI-compatible API."""

import json
import os
import re
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

from megaprompt.core.llm_base import LLMClientBase

# OpenRouter endpoint
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1"

# Popular models on OpenRouter (user can specify any model)
POPULAR_OPENROUTER_MODELS = [
    "openai/gpt-4o",
    "xiaomi/mimo-v2-flash:free",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-opus",
    "google/gemini-2.0-flash-exp",
    "meta-llama/llama-3.1-70b-instruct",
    "mistralai/mixtral-8x7b-instruct",
]


class OpenRouterClient:
    """Client for interacting with OpenRouter API (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "xiaomi/mimo-v2-flash:free",
        temperature: float = 0.0,
        seed: Optional[int] = None,
    ):
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            base_url: Base URL for OpenRouter API (defaults to https://openrouter.ai/api/v1)
            model: Model name to use (default: xiaomi/mimo-v2-flash:free)
            temperature: Temperature for generation (0.0 for determinism)
            seed: Random seed for determinism
        """
        if OpenAI is None:
            raise ImportError(
                "openai package is required for OpenRouter support. Install it with: pip install openai"
            )

        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is required for OpenRouter provider. "
                "Get your API key from https://openrouter.ai/keys"
            )

        # Clean API key (remove quotes if present)
        self.api_key = self.api_key.strip().strip('"').strip("'")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY cannot be empty. Please provide a valid API key from "
                "https://openrouter.ai/keys"
            )

        # Default OpenRouter API base URL
        self.base_url = base_url or os.getenv("OPENROUTER_API_BASE", OPENROUTER_ENDPOINT)
        self.model = model or os.getenv("OPENROUTER_MODEL", "xiaomi/mimo-v2-flash:free")
        self.temperature = temperature
        self.seed = seed

        # Initialize OpenAI client for OpenRouter
        # OpenRouter requires HTTP-Referer and X-Title headers (optional but recommended)
        default_headers = {
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://github.com/megaprompt"),
            "X-Title": os.getenv("OPENROUTER_X_TITLE", "MegaPrompt Generator"),
        }
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers=default_headers,
        )

    def generate(
        self,
        prompt: str,
        max_retries: int = 3,
        timeout: int = 120,
    ) -> str:
        """
        Generate response from OpenRouter API.

        Args:
            prompt: Input prompt
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds

        Returns:
            Generated text response

        Raises:
            RuntimeError: If API call fails after retries
        """
        for attempt in range(max_retries):
            try:
                extra_body = {}
                if self.seed is not None:
                    extra_body["seed"] = self.seed

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    extra_body=extra_body if extra_body else None,
                    timeout=timeout,
                )

                # Extract response text
                if response.choices and len(response.choices) > 0:
                    return response.choices[0].message.content or ""
                return ""

            except Exception as e:
                error_msg = str(e)
                error_lower = error_msg.lower()

                if attempt == max_retries - 1:
                    # Provide helpful error messages
                    if "401" in error_msg or "unauthorized" in error_lower or "invalid_api_key" in error_lower or "authentication" in error_lower:
                        raise RuntimeError(
                            f"OpenRouter API authentication failed (401 Unauthorized).\n\n"
                            f"Current configuration:\n"
                            f"  - Endpoint: {self.base_url}\n"
                            f"  - Model: {self.model}\n\n"
                            f"Possible causes:\n"
                            f"1. Invalid API key - Check your OPENROUTER_API_KEY environment variable\n"
                            f"2. API key not activated - Verify key is active in OpenRouter dashboard\n"
                            f"3. Rate limits - You may have exceeded your API quota\n\n"
                            f"Troubleshooting:\n"
                            f"- Get API key from: https://openrouter.ai/keys\n"
                            f"- Verify key is active in OpenRouter dashboard\n"
                            f"- Check API key format and ensure no extra spaces\n"
                            f"- Original error: {error_msg}"
                        ) from e
                    elif "404" in error_msg or "not found" in error_lower or "model" in error_lower and ("not found" in error_lower or "invalid" in error_lower):
                        raise RuntimeError(
                            f"OpenRouter model '{self.model}' not found (404).\n\n"
                            f"Popular models:\n"
                            f"  {', '.join(POPULAR_OPENROUTER_MODELS[:5])}\n\n"
                            f"Browse all models at: https://openrouter.ai/models\n\n"
                            f"Set model with: --model xiaomi/mimo-v2-flash:free\n"
                            f"Or set OPENROUTER_MODEL environment variable.\n\n"
                            f"Original error: {error_msg}"
                        ) from e
                    elif "timeout" in error_lower or "connection" in error_lower or "network" in error_lower:
                        raise RuntimeError(
                            f"Network error connecting to OpenRouter API.\n\n"
                            f"Possible causes:\n"
                            f"1. Network connectivity issues\n"
                            f"2. Firewall blocking requests to {self.base_url}\n"
                            f"3. API endpoint unreachable\n"
                            f"4. Request timeout (current timeout: {timeout}s)\n\n"
                            f"Troubleshooting:\n"
                            f"- Check your internet connection\n"
                            f"- Verify firewall settings\n"
                            f"- Try increasing timeout value\n"
                            f"- Original error: {error_msg}"
                        ) from e
                    else:
                        raise RuntimeError(
                            f"Failed to generate response from OpenRouter API after {max_retries} attempts.\n"
                            f"Error: {error_msg}\n\n"
                            f"Troubleshooting:\n"
                            f"- Check OpenRouter status: https://status.openrouter.ai/\n"
                            f"- Verify model name and API key\n"
                            f"- Browse models: https://openrouter.ai/models"
                        ) from e
                # Continue to retry

        raise RuntimeError(f"Failed to generate response after {max_retries} attempts")

    def extract_json(self, text: str) -> dict:
        """
        Extract JSON from AI response, handling markdown code blocks.

        Args:
            text: Raw response text that may contain JSON

        Returns:
            Parsed JSON as dictionary

        Raises:
            ValueError: If no valid JSON is found
        """
        # Try to find JSON in markdown code blocks first
        json_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(json_block_pattern, text, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Try to find JSON object directly
        json_object_pattern = r"\{.*\}"
        match = re.search(json_object_pattern, text, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Try parsing the entire text as JSON
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        raise ValueError(f"Could not extract valid JSON from response: {text[:200]}...")

