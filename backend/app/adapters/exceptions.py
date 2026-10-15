"""Exceptions raised by model adapters."""


class ModelAdapterException(Exception):
    """Base exception for all model adapter errors."""
    pass


class ModelUnavailableException(ModelAdapterException, RuntimeError):
    """Raised when the model is not configured, uninitialized, or unavailable."""
    pass


class ModelAuthenticationException(ModelAdapterException):
    """Raised when authentication to the remote model provider fails (401/403)."""
    pass


class ModelRateLimitException(ModelAdapterException):
    """Raised when remote inference encounters rate limiting or quota exhaustion (429)."""
    pass


class ModelNetworkException(ModelAdapterException):
    """Raised on network timeout, unreachable host, or transport error."""
    pass


class ModelInferenceException(ModelAdapterException):
    """Raised when remote inference fails, returns 5xx, or yields malformed output."""
    pass
