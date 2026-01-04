"""
OpenAI API adapter for LLM calls.

This module provides an implementation of ModelAdapter that uses the OpenAI API.
"""
import time
from typing import Optional

from ytce.ai.models.base import ModelAdapter
from ytce.ai.models.errors import (
    ModelAPIError,
    ModelAuthenticationError,
    ModelRateLimitError,
    ModelTimeoutError,
)
from ytce.ai.models.tokens import TokenUsage
from ytce.ai.models.tokens import TokenUsage


class OpenAIAdapter(ModelAdapter):
    """
    OpenAI API adapter implementation.
    
    Uses the OpenAI API to generate responses. Handles:
    - API authentication
    - Rate limiting with exponential backoff
    - Error handling
    - Retries for transient failures
    """
    
    def __init__(
        self,
        api_key: str,
        model: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 60.0,
    ):
        """
        Initialize OpenAI adapter.
        
        Args:
            api_key: OpenAI API key
            model: Model identifier (e.g., "gpt-4.1-nano", "gpt-4.1-mini")
            max_retries: Maximum number of retry attempts for failed requests
            retry_delay: Initial delay between retries (seconds)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # Lazy import to avoid requiring openai package if not used
        try:
            import openai
            self._openai = openai
        except ImportError:
            raise ImportError(
                "OpenAI package is required. Install it with: pip install openai"
            )
        
        # Initialize OpenAI client
        self._client = self._openai.OpenAI(api_key=api_key, timeout=timeout)
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> str:
        """
        Call OpenAI API and return response.
        
        Implements retry logic with exponential backoff for rate limits
        and transient errors.
        
        Args:
            prompt: The prompt string to send
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens in response
            
        Returns:
            Raw text response from OpenAI
            
        Raises:
            ModelAPIError: If API call fails after retries
            ModelRateLimitError: If rate limit is exceeded
            ModelAuthenticationError: If API key is invalid
            ModelTimeoutError: If request times out
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                # Extract text from response
                if not response.choices:
                    raise ModelAPIError("OpenAI returned empty choices")
                
                content = response.choices[0].message.content
                if content is None:
                    raise ModelAPIError("OpenAI returned None content")
                
                # Extract token usage
                usage = response.usage
                token_usage = TokenUsage(
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    total_tokens=usage.total_tokens if usage else 0,
                    cached_tokens=getattr(usage, "cache_creation_input_tokens", None) if usage else None,
                )
                
                return content, token_usage
                
            except self._openai.RateLimitError as e:
                last_error = ModelRateLimitError(
                    f"OpenAI rate limit exceeded: {str(e)}",
                    response=str(e),
                )
                if attempt < self.max_retries:
                    # Exponential backoff for rate limits
                    delay = self.retry_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                raise last_error
                
            except self._openai.AuthenticationError as e:
                raise ModelAuthenticationError(
                    f"OpenAI authentication failed: {str(e)}",
                    response=str(e),
                )
                
            except self._openai.APITimeoutError as e:
                last_error = ModelTimeoutError(
                    f"OpenAI request timed out: {str(e)}",
                )
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                raise last_error
                
            except self._openai.APIError as e:
                # Check if it's a retryable error
                status_code = getattr(e, "status_code", None)
                if status_code and status_code >= 500 and attempt < self.max_retries:
                    # Server error, retry
                    last_error = ModelAPIError(
                        f"OpenAI API error: {str(e)}",
                        status_code=status_code,
                        response=str(e),
                    )
                    delay = self.retry_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                
                # Non-retryable error
                raise ModelAPIError(
                    f"OpenAI API error: {str(e)}",
                    status_code=status_code,
                    response=str(e),
                )
                
            except Exception as e:
                # Unexpected error
                raise ModelAPIError(
                    f"Unexpected error calling OpenAI: {str(e)}",
                    response=str(e),
                )
        
        # If we exhausted retries, raise last error
        if last_error:
            raise last_error
        else:
            raise ModelAPIError("Failed to generate response after retries")
    
    def get_model_name(self) -> str:
        """Get the model identifier."""
        return self.model


class MockAdapter(ModelAdapter):
    """
    Mock adapter for testing and dry-run mode.
    
    Returns a predictable mock response without making actual API calls.
    Useful for testing and previewing prompts.
    """
    
    def __init__(self, model: str):
        """
        Initialize mock adapter.
        
        Args:
            model: Model identifier (for consistency with real adapters)
        """
        self.model = model
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ):
        """
        Return mock JSON response.
        
        Returns a simple mock response that matches the expected JSON format.
        Extracts actual comment IDs and labels from the prompt.
        """
        import re
        import json
        
        # Extract comment IDs from prompt
        # Pattern: "ID: <comment_id>"
        id_pattern = r'ID:\s*([^\n]+)'
        comment_ids = re.findall(id_pattern, prompt)
        
        # If no IDs found, fall back to counting comments
        if not comment_ids:
            comment_count = prompt.count("Comment ")
            comment_ids = [f"comment_{i+1}" for i in range(comment_count)]
        
        # Try to extract labels from prompt (for classification tasks)
        # Look for patterns like: "must be exactly one of: "yes", "no""
        label_pattern = r'must be exactly one of:\s*([^\n]+)'
        label_matches = re.findall(label_pattern, prompt)
        
        # Also try: "Available categories: "positive", "neutral", "negative""
        if not label_matches:
            category_pattern = r'Available categories:\s*([^\n]+)'
            label_matches = re.findall(category_pattern, prompt)
        
        # Also try: "Available labels: "topic1", "topic2""
        if not label_matches:
            labels_pattern = r'Available labels:\s*([^\n]+)'
            label_matches = re.findall(labels_pattern, prompt)
        
        # Extract labels from quoted strings
        labels = []
        if label_matches:
            quoted_labels = re.findall(r'"([^"]+)"', label_matches[0])
            labels = quoted_labels
        
        # Try to detect task type and generate appropriate mock values
        mock_value = None
        is_translation = False
        target_language = None
        comment_texts = []
        
        # Check for translation task
        if "translation" in prompt.lower() or "translate" in prompt.lower():
            is_translation = True
            # Extract target language (e.g., "to Russian", "target language: Russian")
            lang_patterns = [
                r'translate.*?to\s+([A-Za-z]+)',
                r'target language[:\s]+([A-Za-z]+)',
                r'language[:\s]+([A-Za-z]+)',
            ]
            for pattern in lang_patterns:
                lang_match = re.search(pattern, prompt, re.IGNORECASE)
                if lang_match:
                    target_language = lang_match.group(1)
                    break
            
            # Extract comment texts from prompt for mock translation
            text_pattern = r'Text:\s*([^\n]+)'
            comment_texts = re.findall(text_pattern, prompt)
            
            if comment_texts:
                # Use actual comment texts to generate mock translations
                mock_value = "TRANSLATION_PLACEHOLDER"  # Special marker
            else:
                mock_value = "[Mock Translation]"
        
        elif "scoring" in prompt.lower() or "score" in prompt.lower():
            # Scoring task - extract scale
            scale_pattern = r'Score range:\s*([\d.]+)\s*to\s*([\d.]+)'
            scale_match = re.search(scale_pattern, prompt)
            if scale_match:
                min_score = float(scale_match.group(1))
                max_score = float(scale_match.group(2))
                mock_value = (min_score + max_score) / 2.0
            else:
                mock_value = 0.5
        elif "multi_label" in prompt.lower() or "multiple labels" in prompt.lower():
            # Multi-label - use first label if available
            mock_value = labels[:1] if labels else ["mock_label"]
        elif labels:
            # Classification - use first label
            mock_value = labels[0]
        else:
            # Fallback
            mock_value = "mock_value"
        
        # Generate mock results
        results = []
        for i, comment_id in enumerate(comment_ids):
            comment_id = comment_id.strip()
            
            # Handle translation tasks specially
            if is_translation and mock_value == "TRANSLATION_PLACEHOLDER":
                # Extract the corresponding comment text
                if i < len(comment_texts):
                    original_text = comment_texts[i].strip()
                    # Generate a mock translation with language prefix
                    lang_prefix = target_language[:2].upper() if target_language else "RU"
                    value = f"[{lang_prefix}] {original_text}"
                else:
                    value = f"[{target_language or 'RU'}] [Mock Translation]"
            # Alternate between labels for variety (if multiple labels available)
            elif isinstance(mock_value, list):
                value = mock_value
            elif isinstance(mock_value, str) and len(labels) > 1:
                # Alternate between labels
                value = labels[i % len(labels)]
            else:
                value = mock_value
            
            results.append({
                "comment_id": comment_id,
                "value": value,
                "confidence": 0.85
            })
        
        response_text = json.dumps(results, indent=2)
        
        # Mock token usage (rough estimate)
        from ytce.ai.models.tokens import TokenUsage
        mock_token_usage = TokenUsage(
            prompt_tokens=len(prompt.split()) // 2,  # Rough estimate
            completion_tokens=len(response_text.split()) // 2,
            total_tokens=len(prompt.split()) // 2 + len(response_text.split()) // 2,
        )
        
        return response_text, mock_token_usage
    
    def get_model_name(self) -> str:
        """Get the model identifier."""
        return self.model


def create_adapter(
    model: str,
    api_key: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    timeout: float = 60.0,
    dry_run: bool = False,
) -> ModelAdapter:
    """
    Factory function to create a ModelAdapter instance.
    
    Currently only supports OpenAI, but can be extended to support
    other providers based on model name or configuration.
    
    Args:
        model: Model identifier (e.g., "gpt-4.1-nano")
        api_key: API key for the provider (ignored if dry_run=True)
        max_retries: Maximum retry attempts
        retry_delay: Initial retry delay
        timeout: Request timeout
        dry_run: If True, return MockAdapter instead of real adapter
        
    Returns:
        ModelAdapter instance
        
    Raises:
        ValueError: If model provider is not supported
    """
    if dry_run:
        return MockAdapter(model=model)
    
    # For now, assume all models are OpenAI
    # In the future, we can add logic to detect provider from model name
    if model.startswith("gpt-"):
        return OpenAIAdapter(
            api_key=api_key,
            model=model,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
        )
    else:
        raise ValueError(
            f"Unsupported model: {model}. "
            "Currently only OpenAI models (gpt-*) are supported."
        )


__all__ = [
    "OpenAIAdapter",
    "MockAdapter",
    "create_adapter",
]

