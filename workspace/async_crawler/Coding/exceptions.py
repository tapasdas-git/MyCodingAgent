"""Custom exceptions raised by the async crawler."""

from __future__ import annotations


class CrawlFetchError(RuntimeError):
    """Raised when a fetch cannot be completed successfully."""

    def __init__(
        self,
        message: str,
        *,
        url: str | None = None,
        status_code: int | None = None,
        attempts: int | None = None,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        self.attempts = attempts


class CrawlTimeoutError(CrawlFetchError):
    """Raised when a fetch exceeds its configured timeout."""
