"""Ollama LLM client wrapper with JSON extraction and deterministic mode."""

import json
import os
import re
from typing import Optional

from ollama import Client

from megaprompt.core.llm_base import LLMClientBase


class OllamaClient:
    """
    Client for interacting with Ollama API.
    
    Implements LLMClientBase protocol.
    """
    """Client for interacting with Ollama API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = "llama3.1",
        temperature: float = 0.0,
        seed: Optional[int] = None,
    ):
        """
        Initialize Ollama client.

        Args:
            base_url: Base URL for Ollama API (defaults to http://localhost:11434)
            model: Model name to use (default: llama3.1)
            temperature: Temperature for generation (0.0 for determinism)
            seed: Random seed for determinism
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1")
        self.temperature = temperature
        self.seed = seed
        self.client = Client(host=self.base_url)

    def generate(
        self,
        prompt: str,
        max_retries: int = 3,
        timeout: int = 120,
    ) -> str:
        """
        Generate response from Ollama.

        Args:
            prompt: Input prompt
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds

        Returns:
            Generated text response

        Raises:
            requests.RequestException: If API call fails after retries
        """
        options = {
            "temperature": self.temperature,
        }
        if self.seed is not None:
            options["seed"] = self.seed

        for attempt in range(max_retries):
            try:
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    options=options,
                    stream=False,
                )
                return response.get("response", "")
            except Exception as e:
                error_msg = str(e)
                # Check if it's a model not found error
                if "not found" in error_msg.lower() or "404" in error_msg:
                    # Try to get list of available models for better error message
                    try:
                        available_models = self.client.list()
                        model_names = [m.get("name", "") for m in available_models.get("models", [])]
                        if model_names:
                            suggested_models = ", ".join(model_names[:3])  # Show first 3
                            error_msg = (
                                f"Model '{self.model}' not found. "
                                f"Available models: {suggested_models}. "
                                f"Use 'ollama list' to see all models, or pull one with 'ollama pull <model>'"
                            )
                    except Exception:
                        # If we can't list models, just use the original error
                        pass
                    raise RuntimeError(error_msg) from e
                elif attempt == max_retries - 1:
                    raise RuntimeError(f"Failed to generate response after {max_retries} attempts: {e}") from e
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

