"""
Model layer for LLM provider adapters.

This module provides adapters for different LLM providers (OpenAI, etc.)
with a unified interface for making API calls.
"""
from ytce.ai.models.base import ModelAdapter
from ytce.ai.models.errors import (
    ModelAPIError,
    ModelAuthenticationError,
    ModelError,
    ModelInvalidResponseError,
    ModelRateLimitError,
    ModelTimeoutError,
)
from ytce.ai.models.openai import MockAdapter, OpenAIAdapter, create_adapter

__all__ = [
    # Base interface
    "ModelAdapter",
    # Implementations
    "OpenAIAdapter",
    "MockAdapter",
    "create_adapter",
    # Errors
    "ModelError",
    "ModelAPIError",
    "ModelRateLimitError",
    "ModelAuthenticationError",
    "ModelTimeoutError",
    "ModelInvalidResponseError",
]

