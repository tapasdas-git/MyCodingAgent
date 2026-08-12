from __future__ import annotations

import sys
from pathlib import Path

import pytest


CODING_DIR = Path(__file__).resolve().parents[1] / "Coding"
if str(CODING_DIR) not in sys.path:
    sys.path.insert(0, str(CODING_DIR))

from limiter import RateLimiterService, TokenBucket  # noqa: E402
from schemas import BucketConfig, RateLimitRequest  # noqa: E402


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.current = start

    def __call__(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


def test_burst_requests_allow_until_capacity_is_exhausted() -> None:
    clock = FakeClock()
    config = BucketConfig(capacity=5, refill_rate_per_second=1)
    service = RateLimiterService(default_config=config, clock=clock)

    result = service.allow_request(RateLimitRequest(key="client-a", tokens=3))

    assert result.allowed is True
    assert result.available_tokens == pytest.approx(5)
    assert result.remaining_tokens == pytest.approx(2)
    assert result.bucket_created is True

    second = service.allow_request(RateLimitRequest(key="client-a", tokens=2))
    assert second.allowed is True
    assert second.remaining_tokens == pytest.approx(0)


def test_bucket_exhaustion_blocks_requests() -> None:
    clock = FakeClock()
    service = RateLimiterService(
        default_config=BucketConfig(capacity=2, refill_rate_per_second=0),
        clock=clock,
    )

    first = service.allow_request(RateLimitRequest(key="client-b", tokens=2))
    blocked = service.allow_request(RateLimitRequest(key="client-b", tokens=1))

    assert first.allowed is True
    assert blocked.allowed is False
    assert blocked.remaining_tokens == pytest.approx(0)
    assert blocked.retry_after_seconds is None


def test_time_based_refill_restores_tokens() -> None:
    clock = FakeClock()
    bucket = TokenBucket(BucketConfig(capacity=10, refill_rate_per_second=2), clock=clock)

    allowed, available, remaining, retry_after, _ = bucket.consume(7)
    assert allowed is True
    assert available == pytest.approx(10)
    assert remaining == pytest.approx(3)
    assert retry_after is None

    clock.advance(1.5)
    allowed_again, available_again, remaining_again, retry_after_again, _ = bucket.consume(5)
    assert allowed_again is True
    assert available_again == pytest.approx(6)
    assert remaining_again == pytest.approx(1)
    assert retry_after_again is None


def test_multi_client_tracking_isolated_by_key() -> None:
    clock = FakeClock()
    service = RateLimiterService(
        default_config=BucketConfig(capacity=4, refill_rate_per_second=0),
        clock=clock,
    )

    service.configure_bucket("client-x", BucketConfig(capacity=1, refill_rate_per_second=0))
    service.configure_bucket("client-y", BucketConfig(capacity=3, refill_rate_per_second=0))

    x_result = service.allow_request(RateLimitRequest(key="client-x", tokens=1))
    y_result = service.allow_request(RateLimitRequest(key="client-y", tokens=2))
    x_blocked = service.allow_request(RateLimitRequest(key="client-x", tokens=1))

    assert x_result.allowed is True
    assert y_result.allowed is True
    assert y_result.remaining_tokens == pytest.approx(1)
    assert x_blocked.allowed is False
    assert service.get_status("client-y").remaining_tokens == pytest.approx(1)

