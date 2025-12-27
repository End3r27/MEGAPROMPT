"""LLM client wrapper for adding logging, rate limiting, and cost tracking."""

import time
from typing import Optional

from megaprompt.core.llm_base import LLMClientBase
from megaprompt.core.logging import get_logger
from megaprompt.core.cost_tracker import get_cost_tracker
from megaprompt.core.rate_limit import get_rate_limiter

logger = get_logger("megaprompt.llm_wrapper")


class LoggingLLMClientWrapper:
    """
    Wraps an LLM client to add logging, rate limiting, and cost tracking.
    
    This wrapper intercepts calls to the LLM client and adds:
    - Structured logging of LLM calls (prompts, responses, tokens, latency, cost)
    - Rate limiting to prevent exceeding API limits
    - Cost tracking for budget management
    """

    def __init__(
        self,
        client: LLMClientBase,
        provider: str,
        model: str,
        rate_limit_key: Optional[str] = None,
        track_costs: bool = True,
    ):
        """
        Initialize LLM client wrapper.

        Args:
            client: The underlying LLM client to wrap
            provider: Provider name (e.g., "openai", "gemini")
            model: Model name
            rate_limit_key: Optional rate limit key (defaults to "provider:{provider}:model:{model}")
            track_costs: If True, track costs for API calls
        """
        self.client = client
        self.provider = provider
        self.model = model
        self.rate_limit_key = rate_limit_key or f"provider:{provider}:model:{model}"
        self.track_costs = track_costs

    def generate(self, prompt: str, max_retries: int = 3, timeout: int = 120) -> str:
        """
        Generate response from LLM with logging, rate limiting, and cost tracking.

        Args:
            prompt: Input prompt text
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds

        Returns:
            Generated text response

        Raises:
            RuntimeError: If generation fails after retries
        """
        # Apply rate limiting
        rate_limiter = get_rate_limiter()
        rate_limiter.acquire(self.rate_limit_key, wait=True)

        # Track start time for latency measurement
        start_time = time.time()

        # Call underlying client
        try:
            response = self.client.generate(prompt, max_retries=max_retries, timeout=timeout)
            latency_ms = (time.time() - start_time) * 1000

            # Estimate token usage (rough approximation: 1 token ≈ 4 characters)
            # This is a rough estimate - actual tokenizers vary by model
            estimated_input_tokens = len(prompt) // 4
            estimated_output_tokens = len(response) // 4

            # Track costs
            cost = None
            if self.track_costs:
                try:
                    cost_tracker = get_cost_tracker()
                    cost = cost_tracker.record_usage(
                        provider=self.provider,
                        model=self.model,
                        tokens_input=estimated_input_tokens,
                        tokens_output=estimated_output_tokens,
                    )
                except Exception as e:
                    logger.warning(f"Failed to track costs: {e}")

            # Log LLM call
            logger.log_llm_call(
                provider=self.provider,
                model=self.model,
                prompt=prompt,
                response=response,
                tokens_input=estimated_input_tokens,
                tokens_output=estimated_output_tokens,
                latency_ms=latency_ms,
                cost=cost,
            )

            return response

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            # Log failed call
            logger.error(
                f"LLM call failed: {self.provider}/{self.model}",
                context={
                    "provider": self.provider,
                    "model": self.model,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "latency_ms": latency_ms,
                    "prompt_length": len(prompt),
                },
            )
            raise

    def extract_json(self, text: str) -> dict:
        """
        Extract JSON from AI response.

        Args:
            text: Raw response text that may contain JSON

        Returns:
            Parsed JSON as dictionary

        Raises:
            ValueError: If no valid JSON is found
        """
        # Delegate to underlying client
        return self.client.extract_json(text)


def wrap_client_with_logging(
    client: LLMClientBase,
    provider: str,
    model: str,
    rate_limit_key: Optional[str] = None,
    track_costs: bool = True,
) -> LoggingLLMClientWrapper:
    """
    Wrap an LLM client with logging, rate limiting, and cost tracking.

    Args:
        client: The LLM client to wrap
        provider: Provider name
        model: Model name
        rate_limit_key: Optional rate limit key
        track_costs: If True, track costs

    Returns:
        LoggingLLMClientWrapper instance
    """
    return LoggingLLMClientWrapper(
        client=client,
        provider=provider,
        model=model,
        rate_limit_key=rate_limit_key,
        track_costs=track_costs,
    )

