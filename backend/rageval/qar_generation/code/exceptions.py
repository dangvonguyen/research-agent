"""Custom exception classes for QAR generation pipeline."""


class QARGenerationError(Exception):
    """Base exception for QAR generation errors."""

    pass


class APIError(QARGenerationError):
    """Raised when API calls fail after all retries."""

    pass


class InvalidResponseError(QARGenerationError):
    """Raised when API response is invalid or malformed."""

    pass


class ConfigurationError(QARGenerationError):
    """Raised when configuration is invalid or missing."""

    pass


class ValidationError(QARGenerationError):
    """Raised when data validation fails."""

    pass


class FileOperationError(QARGenerationError):
    """Raised when file operations fail."""

    pass
