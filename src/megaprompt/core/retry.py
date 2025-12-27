"""Enhanced error recovery and retry system for LLM API calls."""

import functools
import time
from typing import Any, Callable, Optional, TypeVar

from megaprompt.core.logging import get_logger

T = TypeVar("T")

logger = get_logger("megaprompt.retry")


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API calls.
    
    Prevents cascading failures by opening the circuit after a threshold
    of failures, allowing it to recover after a cooldown period.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original exception from function call
        """
        if self.state == "open":
            # Check if we should attempt recovery
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time > self.recovery_timeout
            ):
                self.state = "half_open"
                logger.info("Circuit breaker transitioning to half-open state")
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker is open. Will retry after {self.recovery_timeout}s"
                )

        try:
            result = func(*args, **kwargs)
            # Success - reset failure count and close circuit
            if self.state == "half_open":
                self.state = "closed"
                logger.info("Circuit breaker closed after successful call")
            self.failure_count = 0
            return result
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )

            raise


def retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    logger_instance: Optional[Any] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying function calls with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential backoff calculation
        jitter: If True, add random jitter to delay to prevent thundering herd
        retryable_exceptions: Tuple of exception types that should trigger retry
        logger_instance: Optional logger instance for logging retries

    Returns:
        Decorator function
    """
    if logger_instance is None:
        logger_instance = logger

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        # Add jitter if enabled
                        if jitter:
                            import random
                            jitter_amount = delay * 0.1 * random.random()
                            actual_delay = delay + jitter_amount
                        else:
                            actual_delay = delay

                        logger_instance.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {actual_delay:.2f}s...",
                            context={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_retries": max_retries,
                                "delay": actual_delay,
                            },
                        )

                        time.sleep(actual_delay)

                        # Calculate next delay with exponential backoff
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        logger_instance.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}",
                            context={
                                "function": func.__name__,
                                "max_retries": max_retries,
                                "error": str(e),
                            },
                        )

            # All retries exhausted
            raise last_exception

        return wrapper

    return decorator


def retry_with_circuit_breaker(
    circuit_breaker: CircuitBreaker,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    logger_instance: Optional[Any] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator combining retry logic with circuit breaker pattern.

    Args:
        circuit_breaker: CircuitBreaker instance
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exception types that should trigger retry
        logger_instance: Optional logger instance for logging retries

    Returns:
        Decorator function
    """
    if logger_instance is None:
        logger_instance = logger

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    # Use circuit breaker to execute the function
                    return circuit_breaker.call(func, *args, **kwargs)
                except CircuitBreakerError as e:
                    # Circuit breaker is open - don't retry
                    logger_instance.error(
                        f"Circuit breaker open for {func.__name__}: {e}",
                        context={"function": func.__name__},
                    )
                    raise
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger_instance.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {delay:.2f}s...",
                            context={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_retries": max_retries,
                                "delay": delay,
                            },
                        )

                        time.sleep(delay)

                        # Calculate next delay with exponential backoff
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        logger_instance.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}",
                            context={
                                "function": func.__name__,
                                "max_retries": max_retries,
                                "error": str(e),
                            },
                        )

            # All retries exhausted
            raise last_exception

        return wrapper

    return decorator

