"""Pydantic schemas for the token bucket rate limiter."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BucketConfig(BaseModel):
    """Static configuration for an individual token bucket."""

    model_config = ConfigDict(extra="forbid")

    capacity: int = Field(gt=0, description="Maximum number of tokens the bucket can hold.")
    refill_rate_per_second: float = Field(
        ge=0,
        description="Tokens added per second while the bucket is not full.",
    )
    initial_tokens: float | None = Field(
        default=None,
        ge=0,
        description="Optional starting token count. Defaults to the bucket capacity.",
    )


class RateLimitRequest(BaseModel):
    """Request to consume tokens for a given client/key."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, description="Client or tenant identifier.")
    tokens: int = Field(default=1, gt=0, description="Number of tokens to consume.")


class RateLimitResult(BaseModel):
    """Status response from the rate limiter."""

    model_config = ConfigDict(extra="forbid")

    key: str
    allowed: bool
    requested_tokens: int = Field(ge=0)
    available_tokens: float = Field(ge=0)
    remaining_tokens: float = Field(ge=0)
    capacity: int = Field(gt=0)
    refill_rate_per_second: float = Field(ge=0)
    retry_after_seconds: float | None = Field(default=None, ge=0)
    observed_at: float | None = Field(default=None, ge=0)
    bucket_created: bool = False
