"""Async web content fetcher with per-host concurrency limits and retries."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

import httpx

from exceptions import CrawlFetchError, CrawlTimeoutError
from schemas import CrawlRequest, CrawlResult, FetcherConfig

RETRYABLE_STATUSES = {429, 502, 503, 504}


def _normalized_host(url: httpx.URL) -> str:
    """Return a stable host key for semaphore partitioning."""

    split = urlsplit(str(url))
    hostname = (split.hostname or "").lower()
    if not hostname:
        raise CrawlFetchError("Request URL is missing a host.", url=str(url))

    default_port = 443 if split.scheme == "https" else 80
    if split.port is None or split.port == default_port:
        return hostname
    return f"{hostname}:{split.port}"


class AsyncFetcher:
    """Concurrency-limited HTTP fetcher with deterministic retry backoff.

    Args:
        config: Validated fetcher configuration.
        transport: Optional HTTP transport for fully offline testing.
        sleep: Awaitable delay function, injected for deterministic tests.

    Raises:
        ValueError: If the fetcher is used outside its async context.
    """

    def __init__(
        self,
        config: FetcherConfig | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._config = config or FetcherConfig()
        self._transport = transport
        self._sleep = sleep
        self._client: httpx.AsyncClient | None = None
        self._host_semaphores: dict[str, asyncio.Semaphore] = {}
        self._semaphore_lock = asyncio.Lock()

    async def __aenter__(self) -> "AsyncFetcher":
        """Create the reusable async client."""

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._config.timeout_seconds),
            transport=self._transport,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Close the reusable client deterministically."""

        if self._client is not None:
            await self._client.aclose()
        self._client = None

    async def _get_host_semaphore(self, host_key: str) -> asyncio.Semaphore:
        """Return the semaphore associated with a normalized host."""

        async with self._semaphore_lock:
            semaphore = self._host_semaphores.get(host_key)
            if semaphore is None:
                semaphore = asyncio.Semaphore(self._config.max_concurrent_requests)
                self._host_semaphores[host_key] = semaphore
            return semaphore

    async def fetch(self, request: CrawlRequest) -> CrawlResult:
        """Fetch a single validated request."""

        if self._client is None:
            raise ValueError("AsyncFetcher must be used as an async context manager.")

        host_key = _normalized_host(request.url)
        semaphore = await self._get_host_semaphore(host_key)

        async with semaphore:
            return await self._fetch_with_retries(request)

    async def _fetch_with_retries(self, request: CrawlRequest) -> CrawlResult:
        """Execute the HTTP request with retry handling."""

        assert self._client is not None
        started_at = time.perf_counter()
        total_attempts = self._config.max_retries + 1

        for attempt in range(1, total_attempts + 1):
            try:
                response = await self._client.get(
                    str(request.url),
                    headers=request.headers,
                )
            except asyncio.CancelledError:
                raise
            except httpx.TimeoutException as exc:
                raise CrawlTimeoutError(
                    f"Request to {request.url} timed out.",
                    url=str(request.url),
                    attempts=attempt,
                ) from exc
            except httpx.RequestError as exc:
                raise CrawlFetchError(
                    f"Request to {request.url} failed.",
                    url=str(request.url),
                    attempts=attempt,
                ) from exc

            if response.status_code in RETRYABLE_STATUSES:
                if attempt <= self._config.max_retries:
                    await self._sleep(self._backoff_seconds(attempt))
                    continue
                raise CrawlFetchError(
                    f"Retryable HTTP status {response.status_code} exhausted retries.",
                    url=str(request.url),
                    status_code=response.status_code,
                    attempts=attempt,
                )

            if response.status_code >= 400:
                raise CrawlFetchError(
                    f"HTTP status {response.status_code} returned for {request.url}.",
                    url=str(request.url),
                    status_code=response.status_code,
                    attempts=attempt,
                )

            return CrawlResult(
                request=request,
                status_code=response.status_code,
                content=response.text,
                content_type=response.headers.get("content-type"),
                final_url=str(response.url),
                headers=dict(response.headers),
                attempts=attempt,
                elapsed_seconds=time.perf_counter() - started_at,
            )

        raise CrawlFetchError(
            f"Request to {request.url} exhausted retries without a response.",
            url=str(request.url),
            attempts=total_attempts,
        )

    def _backoff_seconds(self, attempt: int) -> float:
        """Compute the deterministic exponential backoff for an attempt."""

        delay = self._config.initial_backoff_seconds * (
            self._config.backoff_multiplier ** (attempt - 1)
        )
        if self._config.max_backoff_seconds is not None:
            return min(delay, self._config.max_backoff_seconds)
        return delay
