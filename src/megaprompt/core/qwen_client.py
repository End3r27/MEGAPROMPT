"""Qwen AI LLM client wrapper using OpenAI-compatible API."""

import json
import os
import re
import warnings
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

from megaprompt.core.llm_base import LLMClientBase

# Known valid DashScope model names
DASHSCOPE_MODELS = [
    "qwen-plus",
    "qwen-turbo",
    "qwen-max",
    "qwen-max-longcontext",
    "qwen-7b-chat",
    "qwen-14b-chat",
    "qwen-72b-chat",
]

# Correct DashScope endpoints
DASHSCOPE_ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_INTL_ENDPOINT = "https://dashscope-intl.aliyuncs.com/api/v1"


class QwenClient:
    """Client for interacting with Qwen AI API (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "qwen-plus",
        temperature: float = 0.0,
        seed: Optional[int] = None,
    ):
        """
        Initialize Qwen client.

        Args:
            api_key: Qwen API key (defaults to QWEN_API_KEY env var)
            base_url: Base URL for Qwen API (defaults to https://dashscope.aliyuncs.com/compatible-mode/v1)
            model: Model name to use (default: qwen-plus)
            temperature: Temperature for generation (0.0 for determinism)
            seed: Random seed for determinism
        """
        if OpenAI is None:
            raise ImportError(
                "openai package is required for Qwen support. Install it with: pip install openai"
            )

        self.api_key = api_key or os.getenv("QWEN_API_KEY")
        if not self.api_key:
            raise ValueError(
                "QWEN_API_KEY environment variable is required for Qwen provider. "
                "Set it or pass api_key parameter."
            )

        # Clean and validate API key format
        # Remove quotes (common mistake when setting env vars: QWEN_API_KEY="sk-xxx")
        self.api_key = self.api_key.strip().strip('"').strip("'")
        if not self.api_key:
            raise ValueError(
                "QWEN_API_KEY cannot be empty. Please provide a valid API key from "
                "https://dashscope.aliyuncs.com/"
            )

        # Default Qwen API base URL (DashScope OpenAI-compatible endpoint)
        default_base_url = os.getenv("QWEN_API_BASE", DASHSCOPE_ENDPOINT)
        self.base_url = base_url or default_base_url
        
        # Validate DashScope API key format (should start with "sk-")
        # This helps catch common mistakes early
        if "dashscope" in self.base_url.lower():
            if not self.api_key.startswith("sk-"):
                warnings.warn(
                    f"DashScope API key should typically start with 'sk-'. "
                    f"Your key starts with '{self.api_key[:5]}...'. "
                    f"If authentication fails, verify the key is correct.",
                    UserWarning,
                )

        # Validate endpoint URL for DashScope
        if "dashscope" in self.base_url.lower():
            # Accept both standard and international endpoints
            valid_endpoints = [DASHSCOPE_ENDPOINT, DASHSCOPE_INTL_ENDPOINT]
            if self.base_url not in valid_endpoints:
                warnings.warn(
                    f"Using non-standard DashScope endpoint: {self.base_url}\n"
                    f"Recommended endpoints: {DASHSCOPE_ENDPOINT} or {DASHSCOPE_INTL_ENDPOINT}",
                    UserWarning,
                )
            # Ensure we're using a valid endpoint if not explicitly provided
            if base_url is None:  # Only override if not explicitly provided
                self.base_url = DASHSCOPE_ENDPOINT

        self.model = model or os.getenv("QWEN_MODEL", "qwen-plus")
        self.temperature = temperature
        self.seed = seed

        # Validate model name for DashScope
        if "dashscope" in self.base_url.lower() and self.model not in DASHSCOPE_MODELS:
            warnings.warn(
                f"Model '{self.model}' may not be available on DashScope. "
                f"Common models: {', '.join(DASHSCOPE_MODELS[:5])}",
                UserWarning,
            )

        # Initialize OpenAI client
        # For DashScope, we explicitly set the Authorization header to ensure proper format
        # DashScope requires: Authorization: Bearer sk-xxxxx
        # We explicitly set default_headers to ensure the exact format: "Bearer <key>"
        if "dashscope" in self.base_url.lower():
            # Explicitly set Authorization header for DashScope compatibility
            # Format: "Authorization: Bearer sk-xxxxx" (with space after "Bearer")
            # Ensure key is clean (no extra spaces) before formatting
            clean_key = self.api_key.strip()
            default_headers = {
                "Authorization": f"Bearer {clean_key}"
            }
            self.client = OpenAI(
                api_key=self.api_key,  # Keep for library compatibility
                base_url=self.base_url,
                default_headers=default_headers,  # This ensures correct "Bearer <key>" format
            )
        else:
            # For other providers (like OpenRouter), use standard api_key parameter
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )

    def generate(
        self,
        prompt: str,
        max_retries: int = 3,
        timeout: int = 120,
    ) -> str:
        """
        Generate response from Qwen API.

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

                # Prepare headers for OpenRouter if using OpenRouter endpoint
                headers = {}
                if "openrouter.ai" in self.base_url:
                    # OpenRouter supports optional headers
                    headers["HTTP-Referer"] = "https://github.com/megaprompt"  # Optional
                    headers["X-Title"] = "MegaPrompt Generator"  # Optional

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    extra_body=extra_body if extra_body else None,
                    timeout=timeout,
                    extra_headers=headers if headers else None,
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
                        is_dashscope = "dashscope" in self.base_url.lower()
                        if is_dashscope:
                            raise RuntimeError(
                                f"DashScope API authentication failed (401 Unauthorized).\n\n"
                                f"Current configuration:\n"
                                f"  - Endpoint: {self.base_url}\n"
                                f"  - Model: {self.model}\n"
                                f"  - Authorization header: Set as 'Bearer <key>'\n\n"
                                f"Possible causes:\n"
                                f"1. Invalid API key - Check your QWEN_API_KEY environment variable\n"
                                f"2. API key not activated - New keys may take 5-10 minutes to activate\n"
                                f"3. IP restrictions - Your API key may have IP whitelist restrictions\n"
                                f"4. Rate limits - You may have exceeded your API quota\n"
                                f"5. Wrong endpoint - Current: {self.base_url}\n"
                                f"   Try: {DASHSCOPE_ENDPOINT} or {DASHSCOPE_INTL_ENDPOINT}\n\n"
                                f"Troubleshooting:\n"
                                f"- Verify API key in DashScope console: https://dashscope.aliyuncs.com/\n"
                                f"- Check key restrictions and IP whitelist settings\n"
                                f"- Try the international endpoint: export QWEN_API_BASE={DASHSCOPE_INTL_ENDPOINT}\n"
                                f"- Wait 5-10 minutes if you just created the key\n"
                                f"- Original error: {error_msg}"
                            ) from e
                        else:
                            raise RuntimeError(
                                f"Qwen API authentication failed (OpenRouter). "
                                f"Check your QWEN_API_KEY - it may be invalid, expired, or from a different provider. "
                                f"Error: {error_msg}\n"
                                f"For OpenRouter: Get API key from https://openrouter.ai/keys"
                            ) from e
                    elif "404" in error_msg or "not found" in error_lower or "model" in error_lower and ("not found" in error_lower or "invalid" in error_lower):
                        is_dashscope = "dashscope" in self.base_url.lower()
                        if is_dashscope:
                            available_models = ", ".join(DASHSCOPE_MODELS)
                            raise RuntimeError(
                                f"DashScope model '{self.model}' not found (404).\n\n"
                                f"Available DashScope models:\n"
                                f"  {available_models}\n\n"
                                f"Common models:\n"
                                f"  - qwen-plus (recommended for most tasks)\n"
                                f"  - qwen-turbo (faster, lower cost)\n"
                                f"  - qwen-max (highest quality)\n\n"
                                f"Set model with: --model qwen-plus\n"
                                f"Or set QWEN_MODEL environment variable.\n\n"
                                f"Original error: {error_msg}"
                            ) from e
                        else:
                            raise RuntimeError(
                                f"Qwen model '{self.model}' not found. Available models: qwen-plus, qwen-turbo, qwen-max, etc. Error: {error_msg}"
                            ) from e
                    elif "timeout" in error_lower or "connection" in error_lower or "network" in error_lower:
                        raise RuntimeError(
                            f"Network error connecting to Qwen API.\n\n"
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
                        is_dashscope = "dashscope" in self.base_url.lower()
                        error_context = ""
                        if is_dashscope:
                            error_context = (
                                f"\n\nDashScope API troubleshooting:\n"
                                f"- Verify endpoint: {DASHSCOPE_ENDPOINT}\n"
                                f"- Check API key format and restrictions\n"
                                f"- Verify model name: {self.model}\n"
                                f"- Check DashScope console for service status\n"
                            )
                        raise RuntimeError(
                            f"Failed to generate response from Qwen API after {max_retries} attempts.\n"
                            f"Error: {error_msg}{error_context}"
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

