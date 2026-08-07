"""In-memory token bucket rate limiter service."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from schemas import BucketConfig, RateLimitRequest, RateLimitResult


Clock = Callable[[], float]


@dataclass
class TokenBucket:
    """Token bucket that refills over time."""

    config: BucketConfig
    clock: Clock = time.monotonic

    def __post_init__(self) -> None:
        start_tokens = self.config.capacity if self.config.initial_tokens is None else self.config.initial_tokens
        self._tokens = float(min(self.config.capacity, start_tokens))
        self._last_refill = self.clock()

    def _refill(self) -> float:
        now = self.clock()
        elapsed = max(0.0, now - self._last_refill)
        if elapsed > 0 and self._tokens < self.config.capacity:
            replenished = elapsed * self.config.refill_rate_per_second
            self._tokens = min(self.config.capacity, self._tokens + replenished)
        self._last_refill = now
        return now

    @property
    def tokens(self) -> float:
        self._refill()
        return self._tokens

    def consume(self, amount: int) -> tuple[bool, float, float, float | None, float]:
        """Try to consume tokens and return the updated state."""

        observed_at = self._refill()
        available = self._tokens
        if amount <= available:
            self._tokens = available - amount
            return True, available, self._tokens, None, observed_at

        retry_after = None
        deficit = amount - available
        if self.config.refill_rate_per_second > 0:
            retry_after = deficit / self.config.refill_rate_per_second
        return False, available, self._tokens, retry_after, observed_at

    def snapshot(self) -> tuple[float, float]:
        """Expose the current bucket state without consuming tokens."""

        observed_at = self._refill()
        return self._tokens, observed_at


class RateLimiterService:
    """Multi-tenant token bucket rate limiter."""

    def __init__(self, default_config: BucketConfig, clock: Clock = time.monotonic) -> None:
        self.default_config = default_config
        self.clock = clock
        self._buckets: dict[str, TokenBucket] = {}

    def configure_bucket(self, key: str, config: BucketConfig) -> None:
        """Register or replace a bucket configuration for a client key."""

        self._buckets[key] = TokenBucket(config=config, clock=self.clock)

    def _get_bucket(self, key: str, config: BucketConfig | None = None) -> tuple[TokenBucket, bool]:
        bucket = self._buckets.get(key)
        if bucket is not None:
            return bucket, False

        bucket_config = config or self.default_config
        bucket = TokenBucket(config=bucket_config, clock=self.clock)
        self._buckets[key] = bucket
        return bucket, True

    def allow_request(self, request: RateLimitRequest, config: BucketConfig | None = None) -> RateLimitResult:
        """Attempt to consume tokens for the request's key."""

        bucket, created = self._get_bucket(request.key, config=config)
        allowed, available, remaining, retry_after, observed_at = bucket.consume(request.tokens)
        return RateLimitResult(
            key=request.key,
            allowed=allowed,
            requested_tokens=request.tokens,
            available_tokens=available,
            remaining_tokens=remaining,
            capacity=bucket.config.capacity,
            refill_rate_per_second=bucket.config.refill_rate_per_second,
            retry_after_seconds=retry_after,
            observed_at=observed_at,
            bucket_created=created,
        )

    def get_status(self, key: str) -> RateLimitResult:
        """Return a snapshot of the bucket without consuming tokens."""

        bucket, created = self._get_bucket(key)
        available, observed_at = bucket.snapshot()
        return RateLimitResult(
            key=key,
            allowed=True,
            requested_tokens=0,
            available_tokens=available,
            remaining_tokens=available,
            capacity=bucket.config.capacity,
            refill_rate_per_second=bucket.config.refill_rate_per_second,
            retry_after_seconds=None,
            observed_at=observed_at,
            bucket_created=created,
        )
