"""
Token usage tracking and cost calculation.
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class TokenUsage:
    """Token usage for a single API call."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: Optional[int] = None  # For cached input tokens


@dataclass
class CostSummary:
    """Cost summary for an analysis run."""
    total_input_tokens: int = 0
    total_cached_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    input_cost: float = 0.0
    cached_cost: float = 0.0
    output_cost: float = 0.0


# Model pricing per 1M tokens (as of 2025)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4.1": {
        "input": 3.00,
        "cached_input": 0.75,
        "output": 12.00,
    },
    "gpt-4.1-mini": {
        "input": 0.80,
        "cached_input": 0.20,
        "output": 3.20,
    },
    "gpt-4.1-nano": {
        "input": 0.20,
        "cached_input": 0.05,
        "output": 0.80,
    },
    "o4-mini": {
        "input": 4.00,
        "cached_input": 1.00,
        "output": 16.00,
    },
}


def get_model_pricing(model_name: str) -> Optional[Dict[str, float]]:
    """
    Get pricing for a model.
    
    Args:
        model_name: Model identifier (e.g., "gpt-4.1-nano")
        
    Returns:
        Dictionary with input, cached_input, and output prices per 1M tokens, or None if unknown
    """
    # Try exact match first
    if model_name in MODEL_PRICING:
        return MODEL_PRICING[model_name]
    
    # Try prefix matching (e.g., "gpt-4.1-nano" -> "gpt-4.1-nano")
    for prefix, pricing in MODEL_PRICING.items():
        if model_name.startswith(prefix):
            return pricing
    
    return None


def calculate_cost(
    token_usage: TokenUsage,
    model_name: str,
) -> float:
    """
    Calculate cost for token usage.
    
    Args:
        token_usage: TokenUsage object
        model_name: Model identifier
        
    Returns:
        Cost in USD
    """
    pricing = get_model_pricing(model_name)
    if not pricing:
        return 0.0
    
    # Calculate costs
    input_cost = (token_usage.prompt_tokens / 1_000_000) * pricing["input"]
    
    cached_cost = 0.0
    if token_usage.cached_tokens:
        cached_cost = (token_usage.cached_tokens / 1_000_000) * pricing["cached_input"]
        # Subtract cached tokens from input tokens for cost calculation
        input_cost = ((token_usage.prompt_tokens - token_usage.cached_tokens) / 1_000_000) * pricing["input"]
    
    output_cost = (token_usage.completion_tokens / 1_000_000) * pricing["output"]
    
    return input_cost + cached_cost + output_cost


def aggregate_costs(token_usages: list[TokenUsage], model_name: str) -> CostSummary:
    """
    Aggregate token usage and calculate total cost.
    
    Args:
        token_usages: List of TokenUsage objects
        model_name: Model identifier
        
    Returns:
        CostSummary with aggregated statistics
    """
    total_input = sum(t.prompt_tokens for t in token_usages)
    total_cached = sum(t.cached_tokens or 0 for t in token_usages)
    total_output = sum(t.completion_tokens for t in token_usages)
    
    pricing = get_model_pricing(model_name)
    if not pricing:
        return CostSummary(
            total_input_tokens=total_input,
            total_cached_tokens=total_cached,
            total_output_tokens=total_output,
        )
    
    # Calculate costs
    input_cost = ((total_input - total_cached) / 1_000_000) * pricing["input"]
    cached_cost = (total_cached / 1_000_000) * pricing["cached_input"]
    output_cost = (total_output / 1_000_000) * pricing["output"]
    total_cost = input_cost + cached_cost + output_cost
    
    return CostSummary(
        total_input_tokens=total_input,
        total_cached_tokens=total_cached,
        total_output_tokens=total_output,
        total_cost=total_cost,
        input_cost=input_cost,
        cached_cost=cached_cost,
        output_cost=output_cost,
    )


__all__ = [
    "TokenUsage",
    "CostSummary",
    "get_model_pricing",
    "calculate_cost",
    "aggregate_costs",
]

