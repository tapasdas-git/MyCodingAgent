"""Validated Pydantic models for the async crawler module."""

from __future__ import annotations

from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    model_validator,
)


class CrawlRequest(BaseModel):
    """Validated fetch request.

    Args:
        url: Absolute HTTP or HTTPS URL to fetch.
        headers: Optional request headers.

    Raises:
        pydantic.ValidationError: If the URL scheme is not HTTP(S) or the
            headers cannot be validated as a string mapping.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    url: HttpUrl
    headers: dict[str, str] = Field(default_factory=dict)


class CrawlResult(BaseModel):
    """Validated fetch response payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request: CrawlRequest
    status_code: Annotated[int, Field(ge=100, le=599)]
    content: str
    content_type: str | None = None
    final_url: HttpUrl
    headers: dict[str, str] = Field(default_factory=dict)
    attempts: PositiveInt
    elapsed_seconds: NonNegativeFloat


class FetcherConfig(BaseModel):
    """Validated runtime configuration for :class:`~fetcher.AsyncFetcher`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_concurrent_requests: PositiveInt = 5
    timeout_seconds: PositiveFloat = 10.0
    max_retries: NonNegativeInt = 3
    initial_backoff_seconds: PositiveFloat = 0.1
    backoff_multiplier: Annotated[float, Field(gt=1.0)] = 2.0
    max_backoff_seconds: PositiveFloat | None = None

    @model_validator(mode="after")
    def _validate_backoff_bounds(self) -> "FetcherConfig":
        """Ensure optional backoff cap is sensible."""

        if (
            self.max_backoff_seconds is not None
            and self.max_backoff_seconds < self.initial_backoff_seconds
        ):
            raise ValueError("max_backoff_seconds must be >= initial_backoff_seconds")
        return self
