"""Factory for creating LLM provider clients with auto-detection."""

import os
from typing import Optional

import requests

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.gemini_client import GeminiClient
from megaprompt.core.llm_client import OllamaClient
from megaprompt.core.qwen_client import QwenClient


def check_ollama_available(base_url: Optional[str] = None) -> bool:
    """
    Check if Ollama is available and running.

    Args:
        base_url: Ollama base URL to check

    Returns:
        True if Ollama is available, False otherwise
    """
    base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def check_qwen_available() -> bool:
    """
    Check if Qwen API is available (has API key).

    Returns:
        True if QWEN_API_KEY is set, False otherwise
    """
    return bool(os.getenv("QWEN_API_KEY"))


def check_gemini_available() -> bool:
    """
    Check if Gemini API is available (has API key).

    Returns:
        True if GEMINI_API_KEY is set, False otherwise
    """
    return bool(os.getenv("GEMINI_API_KEY"))


def create_client(
    provider: str = "auto",
    model: Optional[str] = None,
    temperature: float = 0.0,
    seed: Optional[int] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> LLMClientBase:
    """
    Create an LLM client for the specified provider.

    Args:
        provider: Provider name ("ollama", "qwen", "gemini", or "auto")
        model: Model name (provider-specific)
        temperature: Generation temperature
        seed: Random seed for determinism
        base_url: Base URL (provider-specific, not used for Gemini)
        api_key: API key (for Qwen or Gemini)

    Returns:
        LLM client instance

    Raises:
        ValueError: If provider is invalid or not available
        ImportError: If required packages are not installed
    """
    if provider == "auto":
        # Auto-detect: prefer Qwen if available, then Gemini, then Ollama
        if check_qwen_available():
            provider = "qwen"
        elif check_gemini_available():
            provider = "gemini"
        elif check_ollama_available(base_url):
            provider = "ollama"
        else:
            raise ValueError(
                "No LLM provider available. "
                "Set QWEN_API_KEY for Qwen, GEMINI_API_KEY for Gemini, or ensure Ollama is running."
            )

    if provider == "ollama":
        if not check_ollama_available(base_url):
            raise ValueError(
                f"Ollama is not available at {base_url or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}. "
                "Please ensure Ollama is running."
            )
        return OllamaClient(
            base_url=base_url,
            model=model or "llama3.1",
            temperature=temperature,
            seed=seed,
        )

    elif provider == "qwen":
        if not check_qwen_available() and not api_key:
            raise ValueError(
                "QWEN_API_KEY environment variable is required for Qwen provider. "
                "Set it or pass api_key parameter."
            )
        return QwenClient(
            api_key=api_key,
            base_url=base_url,
            model=model or "qwen-plus",
            temperature=temperature,
            seed=seed,
        )

    elif provider == "gemini":
        if not check_gemini_available() and not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required for Gemini provider. "
                "Set it or pass api_key parameter. "
                "Get your free API key from: https://aistudio.google.com/app/apikey"
            )
        return GeminiClient(
            api_key=api_key,
            model=model or "gemini-2.5-flash",
            temperature=temperature,
            seed=seed,
        )

    else:
        raise ValueError(
            f"Unknown provider: {provider}. Supported providers: ollama, qwen, gemini, auto"
        )

