"""Rate limiting system for LLM API calls."""

import threading
import time
from collections import defaultdict
from typing import Optional

from megaprompt.core.logging import get_logger

logger = get_logger("megaprompt.rate_limit")


class TokenBucket:
    """
    Token bucket rate limiter implementation.
    
    Allows a certain number of tokens (requests) per time period,
    with tokens refilling at a constant rate.
    """

    def __init__(self, rate: float, capacity: float):
        """
        Initialize token bucket.

        Args:
            rate: Tokens (requests) per second to refill
            capacity: Maximum number of tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> bool:
        """
        Try to acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire (default: 1.0)

        Returns:
            True if tokens were acquired, False if bucket doesn't have enough tokens
        """
        with self.lock:
            now = time.time()
            # Refill tokens based on elapsed time
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait(self, tokens: float = 1.0) -> float:
        """
        Wait until tokens are available, then acquire them.

        Args:
            tokens: Number of tokens to acquire (default: 1.0)

        Returns:
            Number of seconds waited
        """
        start_time = time.time()
        
        while not self.acquire(tokens):
            # Calculate how long to wait
            with self.lock:
                needed = tokens - self.tokens
                wait_time = needed / self.rate if self.rate > 0 else 1.0
            
            # Wait with a small buffer
            time.sleep(min(wait_time + 0.1, 1.0))
        
        elapsed = time.time() - start_time
        if elapsed > 0.01:  # Only log if we actually waited
            logger.debug(
                f"Rate limit wait: {elapsed:.2f}s",
                context={"tokens": tokens, "wait_time": elapsed},
            )
        return elapsed


class RateLimiter:
    """
    Rate limiter with per-provider and per-model limits.
    
    Supports multiple token buckets for different rate limit configurations.
    """

    def __init__(self):
        """Initialize rate limiter."""
        self.buckets: dict[str, TokenBucket] = {}
        self.lock = threading.Lock()

    def add_limit(
        self,
        key: str,
        rate: float,
        capacity: Optional[float] = None,
    ) -> None:
        """
        Add or update a rate limit.

        Args:
            key: Unique identifier for this limit (e.g., "provider:model" or "provider:global")
            rate: Requests per second
            capacity: Maximum burst capacity (defaults to rate * 10)
        """
        if capacity is None:
            capacity = rate * 10  # Default: 10 seconds of capacity

        with self.lock:
            self.buckets[key] = TokenBucket(rate, capacity)
            logger.debug(f"Added rate limit: {key} = {rate} req/s, capacity={capacity}")

    def acquire(
        self,
        key: str,
        tokens: float = 1.0,
        wait: bool = True,
    ) -> bool:
        """
        Acquire tokens from a rate limit bucket.

        Args:
            key: Rate limit key
            tokens: Number of tokens to acquire
            wait: If True, wait until tokens are available; if False, return immediately

        Returns:
            True if tokens were acquired (or will be acquired if wait=True), False if wait=False and not available
        """
        with self.lock:
            if key not in self.buckets:
                # No rate limit configured - allow request
                return True

            bucket = self.buckets[key]

        if wait:
            bucket.wait(tokens)
            return True
        else:
            return bucket.acquire(tokens)

    def get_bucket(self, key: str) -> Optional[TokenBucket]:
        """
        Get rate limit bucket for a key.

        Args:
            key: Rate limit key

        Returns:
            TokenBucket instance, or None if not configured
        """
        with self.lock:
            return self.buckets.get(key)


# Global rate limiter instance
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get or create global rate limiter instance.

    Returns:
        RateLimiter instance
    """
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
    return _global_rate_limiter


def set_provider_limit(
    provider: str,
    requests_per_second: float,
    burst_capacity: Optional[float] = None,
) -> None:
    """
    Set rate limit for a provider.

    Args:
        provider: Provider name (e.g., "openai", "gemini")
        requests_per_second: Maximum requests per second
        burst_capacity: Maximum burst capacity (defaults to requests_per_second * 10)
    """
    limiter = get_rate_limiter()
    limiter.add_limit(f"provider:{provider}", requests_per_second, burst_capacity)
    logger.info(
        f"Set rate limit for provider {provider}: {requests_per_second} req/s",
        context={"provider": provider, "rate": requests_per_second},
    )


def set_model_limit(
    provider: str,
    model: str,
    requests_per_second: float,
    burst_capacity: Optional[float] = None,
) -> None:
    """
    Set rate limit for a specific model.

    Args:
        provider: Provider name
        model: Model name
        requests_per_second: Maximum requests per second
        burst_capacity: Maximum burst capacity (defaults to requests_per_second * 10)
    """
    limiter = get_rate_limiter()
    key = f"provider:{provider}:model:{model}"
    limiter.add_limit(key, requests_per_second, burst_capacity)
    logger.info(
        f"Set rate limit for {provider}/{model}: {requests_per_second} req/s",
        context={"provider": provider, "model": model, "rate": requests_per_second},
    )

