"""Cost tracking system for LLM API usage."""

import json
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from megaprompt.core.logging import get_logger

logger = get_logger("megaprompt.cost_tracker")


# Pricing data (per 1M tokens) - update as needed
# Format: (input_cost_per_1M, output_cost_per_1M)
PRICING_DATA = {
    "openai": {
        "gpt-4": (30.0, 60.0),  # $30/M input, $60/M output
        "gpt-4-turbo": (10.0, 30.0),
        "gpt-3.5-turbo": (0.5, 1.5),
    },
    "gemini": {
        "gemini-2.5-flash": (0.075, 0.30),  # Free tier pricing
        "gemini-pro": (0.50, 1.50),
    },
    "qwen": {
        "qwen-plus": (0.008, 0.008),  # Approximate - adjust based on actual pricing
        "qwen-max": (0.02, 0.02),
    },
    "ollama": {
        "default": (0.0, 0.0),  # Local - no cost
    },
}


class CostTracker:
    """
    Tracks LLM API costs and usage.
    
    Provides cost estimation and tracking per provider, model, and session.
    """

    def __init__(self, budget_limit: Optional[float] = None, history_file: Optional[Path] = None):
        """
        Initialize cost tracker.

        Args:
            budget_limit: Optional budget limit in dollars (raises exception if exceeded)
            history_file: Optional file path to persist cost history
        """
        self.budget_limit = budget_limit
        self.history_file = history_file
        self.lock = threading.Lock()
        
        # Track costs per provider/model
        self.provider_costs: dict[str, float] = defaultdict(float)
        self.model_costs: dict[str, float] = defaultdict(float)
        self.session_costs: dict[str, float] = defaultdict(float)
        
        # Track token usage
        self.provider_tokens: dict[str, dict[str, int]] = defaultdict(lambda: {"input": 0, "output": 0})
        self.model_tokens: dict[str, dict[str, int]] = defaultdict(lambda: {"input": 0, "output": 0})
        
        # Total cost
        self.total_cost = 0.0
        
        # Load history if file exists
        if self.history_file and self.history_file.exists():
            self._load_history()

    def _load_history(self) -> None:
        """Load cost history from file."""
        try:
            data = json.loads(self.history_file.read_text(encoding="utf-8"))
            self.total_cost = data.get("total_cost", 0.0)
            self.provider_costs = defaultdict(float, data.get("provider_costs", {}))
            self.model_costs = defaultdict(float, data.get("model_costs", {}))
            logger.info(f"Loaded cost history: ${self.total_cost:.4f} total")
        except Exception as e:
            logger.warning(f"Failed to load cost history: {e}")

    def _save_history(self) -> None:
        """Save cost history to file."""
        if not self.history_file:
            return
        
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "total_cost": self.total_cost,
                "provider_costs": dict(self.provider_costs),
                "model_costs": dict(self.model_costs),
                "last_updated": datetime.utcnow().isoformat(),
            }
            self.history_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save cost history: {e}")

    def estimate_cost(
        self,
        provider: str,
        model: str,
        tokens_input: int,
        tokens_output: int = 0,
    ) -> float:
        """
        Estimate cost for token usage.

        Args:
            provider: Provider name
            model: Model name
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens

        Returns:
            Estimated cost in dollars
        """
        # Get pricing
        provider_pricing = PRICING_DATA.get(provider, {})
        pricing = provider_pricing.get(model) or provider_pricing.get("default")
        
        if not pricing:
            # Unknown pricing - return 0 (won't track costs)
            return 0.0
        
        input_cost_per_1M, output_cost_per_1M = pricing
        
        # Calculate cost
        input_cost = (tokens_input / 1_000_000) * input_cost_per_1M
        output_cost = (tokens_output / 1_000_000) * output_cost_per_1M
        
        return input_cost + output_cost

    def record_usage(
        self,
        provider: str,
        model: str,
        tokens_input: int,
        tokens_output: int = 0,
        session_id: Optional[str] = None,
    ) -> float:
        """
        Record token usage and calculate cost.

        Args:
            provider: Provider name
            model: Model name
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            session_id: Optional session identifier

        Returns:
            Cost in dollars for this usage

        Raises:
            RuntimeError: If budget limit would be exceeded
        """
        cost = self.estimate_cost(provider, model, tokens_input, tokens_output)
        
        with self.lock:
            # Check budget limit
            if self.budget_limit is not None and self.total_cost + cost > self.budget_limit:
                raise RuntimeError(
                    f"Budget limit of ${self.budget_limit:.2f} would be exceeded. "
                    f"Current cost: ${self.total_cost:.4f}, Requested: ${cost:.4f}"
                )
            
            # Update totals
            self.total_cost += cost
            self.provider_costs[provider] += cost
            self.model_costs[f"{provider}/{model}"] += cost
            if session_id:
                self.session_costs[session_id] += cost
            
            # Update token counts
            self.provider_tokens[provider]["input"] += tokens_input
            self.provider_tokens[provider]["output"] += tokens_output
            self.model_tokens[f"{provider}/{model}"]["input"] += tokens_input
            self.model_tokens[f"{provider}/{model}"]["output"] += tokens_output
            
            # Save history
            self._save_history()
        
        logger.info(
            f"Cost recorded: ${cost:.4f} for {provider}/{model}",
            context={
                "provider": provider,
                "model": model,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "cost": cost,
                "total_cost": self.total_cost,
            },
        )
        
        return cost

    def get_total_cost(self) -> float:
        """Get total cost across all providers."""
        with self.lock:
            return self.total_cost

    def get_provider_cost(self, provider: str) -> float:
        """Get total cost for a provider."""
        with self.lock:
            return self.provider_costs.get(provider, 0.0)

    def get_model_cost(self, provider: str, model: str) -> float:
        """Get total cost for a model."""
        with self.lock:
            return self.model_costs.get(f"{provider}/{model}", 0.0)

    def get_session_cost(self, session_id: str) -> float:
        """Get total cost for a session."""
        with self.lock:
            return self.session_costs.get(session_id, 0.0)

    def get_summary(self) -> dict:
        """
        Get cost summary.

        Returns:
            Dictionary with cost breakdown
        """
        with self.lock:
            return {
                "total_cost": self.total_cost,
                "budget_limit": self.budget_limit,
                "provider_costs": dict(self.provider_costs),
                "model_costs": dict(self.model_costs),
                "provider_tokens": dict(self.provider_tokens),
                "model_tokens": dict(self.model_tokens),
            }

    def reset(self) -> None:
        """Reset all cost tracking (use with caution)."""
        with self.lock:
            self.total_cost = 0.0
            self.provider_costs.clear()
            self.model_costs.clear()
            self.session_costs.clear()
            self.provider_tokens.clear()
            self.model_tokens.clear()
            self._save_history()
        logger.info("Cost tracker reset")


# Global cost tracker instance
_global_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker(
    budget_limit: Optional[float] = None,
    history_file: Optional[Path] = None,
) -> CostTracker:
    """
    Get or create global cost tracker instance.

    Args:
        budget_limit: Optional budget limit in dollars
        history_file: Optional file path to persist cost history

    Returns:
        CostTracker instance
    """
    global _global_cost_tracker
    if _global_cost_tracker is None:
        _global_cost_tracker = CostTracker(budget_limit=budget_limit, history_file=history_file)
    elif budget_limit is not None:
        _global_cost_tracker.budget_limit = budget_limit
    return _global_cost_tracker

