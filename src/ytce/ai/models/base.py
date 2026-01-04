"""
Base model adapter interface.

This module defines the abstract interface that all LLM model adapters must implement.
"""
from abc import ABC, abstractmethod
from typing import Tuple

from ytce.ai.models.tokens import TokenUsage


class ModelAdapter(ABC):
    """
    Abstract base class for LLM model adapters.
    
    This interface provides a clean abstraction over different LLM providers,
    allowing the system to work with OpenAI, Anthropic, or other providers
    without changing the task execution logic.
    
    All adapters must implement the generate() method, which takes a prompt
    and returns the raw text response from the LLM along with token usage.
    """
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> Tuple[str, TokenUsage]:
        """
        Call LLM and return raw response with token usage.
        
        This is the core method that all model adapters must implement.
        It should handle:
        - API communication
        - Error handling and retries
        - Rate limiting
        - Response parsing
        - Token usage tracking
        
        Args:
            prompt: The prompt string to send to the LLM
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens in response
            
        Returns:
            Tuple of (raw text response, TokenUsage object)
            
        Raises:
            ModelAPIError: If API call fails
            ModelRateLimitError: If rate limit is exceeded
            ModelAuthenticationError: If authentication fails
            ModelTimeoutError: If request times out
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the model identifier/name.
        
        Returns:
            String identifier for the model (e.g., "gpt-4.1-nano")
        """
        pass


__all__ = [
    "ModelAdapter",
]

