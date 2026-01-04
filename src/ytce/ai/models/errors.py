"""
Model-specific errors for LLM API interactions.
"""


class ModelError(Exception):
    """Base exception for all model-related errors."""
    pass


class ModelAPIError(ModelError):
    """Error raised when API call fails."""
    
    def __init__(self, message: str, status_code: int = None, response: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ModelRateLimitError(ModelAPIError):
    """Error raised when rate limit is exceeded."""
    pass


class ModelAuthenticationError(ModelAPIError):
    """Error raised when API authentication fails."""
    pass


class ModelTimeoutError(ModelError):
    """Error raised when API call times out."""
    pass


class ModelInvalidResponseError(ModelError):
    """Error raised when API returns invalid or unexpected response."""
    pass


__all__ = [
    "ModelError",
    "ModelAPIError",
    "ModelRateLimitError",
    "ModelAuthenticationError",
    "ModelTimeoutError",
    "ModelInvalidResponseError",
]

