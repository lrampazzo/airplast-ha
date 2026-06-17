"""Exceptions raised by airplast-client."""


class AirplastError(Exception):
    """Base exception for Airplast client errors."""


class AirplastRequestError(AirplastError):
    """Raised when a request cannot be completed at transport level."""


class AirplastAuthError(AirplastError):
    """Raised when authentication or token refresh fails."""
    