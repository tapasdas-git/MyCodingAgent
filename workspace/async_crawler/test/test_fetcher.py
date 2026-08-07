"""Offline tests for the async crawler fetcher."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

CODING_DIR = Path(__file__).resolve().parents[1] / "Coding"
if str(CODING_DIR) not in sys.path:
    sys.path.insert(0, str(CODING_DIR))

from exceptions import CrawlFetchError, CrawlTimeoutError
from fetcher import AsyncFetcher
from schemas import CrawlRequest, FetcherConfig


class SequencedTransport(httpx.AsyncBaseTransport):
    """Async transport that returns preconfigured responses or exceptions."""

    def __init__(self, events: list[object]) -> None:
        self._events = list(events)
        self.requests: list[httpx.Request] = []
        self.closed = False

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if not self._events:
            raise AssertionError("Transport was called more times than expected.")

        event = self._events.pop(0)
        if isinstance(event, Exception):
            raise event
        return event

    async def aclose(self) -> None:
        self.closed = True


class BlockingTransport(httpx.AsyncBaseTransport):
    """Transport that coordinates concurrency assertions."""

    def __init__(self) -> None:
        self.active_by_host: dict[str, int] = {}
        self.max_active_by_host: dict[str, int] = {}
        self.global_active = 0
        self.max_global_active = 0
        self.started = 0
        self.start_event = asyncio.Event()
        self.release_event = asyncio.Event()
        self.lock = asyncio.Lock()
        self.closed = False

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host or ""
        async with self.lock:
            self.started += 1
            self.active_by_host[host] = self.active_by_host.get(host, 0) + 1
            self.max_active_by_host[host] = max(
                self.max_active_by_host.get(host, 0),
                self.active_by_host[host],
            )
            self.global_active += 1
            self.max_global_active = max(self.max_global_active, self.global_active)
            if self.started >= 2:
                self.start_event.set()

        await self.release_event.wait()

        async with self.lock:
            self.active_by_host[host] -= 1
            self.global_active -= 1

        return httpx.Response(
            200,
            request=request,
            headers={"content-type": "text/plain"},
            text=f"ok:{host}",
        )

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_successful_fetch_returns_validated_result_and_closes_client() -> None:
    """A successful fetch should return a typed result and close the client."""

    transport = SequencedTransport(
        [
            httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                text="<html>hello</html>",
                request=httpx.Request("GET", "https://example.com/page"),
            )
        ]
    )
    config = FetcherConfig(
        max_concurrent_requests=2,
        timeout_seconds=5.0,
        max_retries=3,
        initial_backoff_seconds=0.01,
        backoff_multiplier=2.0,
    )

    async with AsyncFetcher(config, transport=transport) as fetcher:
        result = await fetcher.fetch(CrawlRequest(url="https://example.com/page"))

        assert str(result.request.url) == "https://example.com/page"
        assert result.status_code == 200
        assert result.content == "<html>hello</html>"
        assert result.content_type == "text/html; charset=utf-8"
        assert str(result.final_url) == "https://example.com/page"
        assert result.attempts == 1
        assert result.headers["content-type"] == "text/html; charset=utf-8"

    assert transport.closed is True


@pytest.mark.asyncio
async def test_independent_per_host_concurrency_limits_allow_parallel_hosts() -> None:
    """Separate hosts should not share a global semaphore."""

    transport = BlockingTransport()
    config = FetcherConfig(
        max_concurrent_requests=1,
        timeout_seconds=5.0,
        max_retries=0,
        initial_backoff_seconds=0.01,
        backoff_multiplier=2.0,
    )

    async with AsyncFetcher(config, transport=transport) as fetcher:
        task_a = asyncio.create_task(
            fetcher.fetch(CrawlRequest(url="https://a.example/test"))
        )
        task_b = asyncio.create_task(
            fetcher.fetch(CrawlRequest(url="https://b.example/test"))
        )

        await asyncio.wait_for(transport.start_event.wait(), timeout=1.0)
        assert transport.max_global_active == 2
        assert transport.max_active_by_host["a.example"] == 1
        assert transport.max_active_by_host["b.example"] == 1

        transport.release_event.set()
        result_a = await task_a
        result_b = await task_b

    assert str(result_a.final_url) == "https://a.example/test"
    assert str(result_b.final_url) == "https://b.example/test"


@pytest.mark.asyncio
async def test_retry_backoff_progression_is_deterministic() -> None:
    """Retryable responses should use predictable exponential delays."""

    response_request = httpx.Request("GET", "https://example.com/retry")
    transport = SequencedTransport(
        [
            httpx.Response(503, request=response_request),
            httpx.Response(502, request=response_request),
            httpx.Response(200, request=response_request, text="done"),
        ]
    )
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    config = FetcherConfig(
        max_concurrent_requests=1,
        timeout_seconds=5.0,
        max_retries=3,
        initial_backoff_seconds=0.25,
        backoff_multiplier=2.0,
    )

    async with AsyncFetcher(config, transport=transport, sleep=record_sleep) as fetcher:
        result = await fetcher.fetch(CrawlRequest(url="https://example.com/retry"))

    assert result.attempts == 3
    assert delays == [0.25, 0.5]
    assert len(transport.requests) == 3


@pytest.mark.asyncio
async def test_retry_exhaustion_raises_domain_error() -> None:
    """Exhausted retryable failures should raise CrawlFetchError."""

    request = httpx.Request("GET", "https://example.com/exhaust")
    transport = SequencedTransport(
        [
            httpx.Response(503, request=request),
            httpx.Response(503, request=request),
            httpx.Response(503, request=request),
        ]
    )
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    config = FetcherConfig(
        max_concurrent_requests=1,
        timeout_seconds=5.0,
        max_retries=2,
        initial_backoff_seconds=0.25,
        backoff_multiplier=2.0,
    )

    with pytest.raises(CrawlFetchError) as excinfo:
        async with AsyncFetcher(config, transport=transport, sleep=record_sleep) as fetcher:
            await fetcher.fetch(CrawlRequest(url="https://example.com/exhaust"))

    assert "exhausted retries" in str(excinfo.value).lower()
    assert delays == [0.25, 0.5]
    assert len(transport.requests) == 3


@pytest.mark.asyncio
async def test_non_retryable_failure_raises_immediately() -> None:
    """Non-retryable HTTP responses should fail without backoff."""

    request = httpx.Request("GET", "https://example.com/missing")
    transport = SequencedTransport([httpx.Response(404, request=request)])
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    async with AsyncFetcher(transport=transport, sleep=record_sleep) as fetcher:
        with pytest.raises(CrawlFetchError) as excinfo:
            await fetcher.fetch(CrawlRequest(url="https://example.com/missing"))

    assert "404" in str(excinfo.value)
    assert delays == []


@pytest.mark.asyncio
async def test_timeout_raises_domain_timeout_error() -> None:
    """Transport timeouts should convert to CrawlTimeoutError."""

    request = httpx.Request("GET", "https://example.com/slow")
    transport = SequencedTransport([httpx.ReadTimeout("timed out", request=request)])

    async with AsyncFetcher(transport=transport) as fetcher:
        with pytest.raises(CrawlTimeoutError):
            await fetcher.fetch(CrawlRequest(url="https://example.com/slow"))


@pytest.mark.asyncio
async def test_cancellation_propagates() -> None:
    """Cancellation should not be converted into a domain failure."""

    release_event = asyncio.Event()

    class CancellableTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            await release_event.wait()
            return httpx.Response(200, request=request, text="late")

        async def aclose(self) -> None:
            return None

    async with AsyncFetcher(transport=CancellableTransport()) as fetcher:
        task = asyncio.create_task(
            fetcher.fetch(CrawlRequest(url="https://example.com/cancel"))
        )
        await asyncio.sleep(0)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task


def test_schema_validation_rejects_invalid_inputs() -> None:
    """Model validation should reject invalid URLs and config values."""

    with pytest.raises(ValidationError):
        CrawlRequest(url="ftp://example.com")

    with pytest.raises(ValidationError):
        FetcherConfig(max_concurrent_requests=0)

    with pytest.raises(ValidationError):
        FetcherConfig(max_retries=-1)

    with pytest.raises(ValidationError):
        FetcherConfig(initial_backoff_seconds=0)
