class TransientToolError(Exception):
    """Raised by a tool for retryable failures (timeouts, 5xx, rate limits)."""


class ToolInputError(Exception):
    """Raised when tool arguments fail validation. Not retried."""
