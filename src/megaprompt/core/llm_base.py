"""Abstract base class for LLM clients."""

from abc import ABC, abstractmethod
from typing import Protocol


class LLMClientBase(Protocol):
    """
    Protocol/interface for LLM clients.
    
    All LLM provider implementations must implement these methods.
    """

    def generate(self, prompt: str, max_retries: int = 3, timeout: int = 120) -> str:
        """
        Generate response from LLM.

        Args:
            prompt: Input prompt text
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds

        Returns:
            Generated text response

        Raises:
            RuntimeError: If generation fails after retries
        """
        ...

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
        ...

