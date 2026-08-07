"""Asynchronous priority scheduler with retry, timeout, and category limits."""

from __future__ import annotations

import asyncio
import inspect
import math
import time
from dataclasses import dataclass
from itertools import count
from typing import Any, Awaitable, Callable

try:  # pragma: no cover - import resolution depends on how the module is loaded.
    from .exceptions import TaskExecutionError, TaskTimeoutError
    from .schemas import SchedulerConfig, TaskJob, TaskResult
except ImportError:  # pragma: no cover - fallback for direct path-based imports.
    from exceptions import TaskExecutionError, TaskTimeoutError
    from schemas import SchedulerConfig, TaskJob, TaskResult

SleepFn = Callable[[float], Awaitable[None]]
ClockFn = Callable[[], float]


@dataclass(slots=True)
class _QueueItem:
    """Validated queue payload tracked by the worker pool."""

    job: TaskJob
    future: asyncio.Future[TaskResult]


class PriorityScheduler:
    """Priority-aware worker pool that executes jobs from an asyncio queue."""

    def __init__(
        self,
        config: SchedulerConfig,
        *,
        sleep: SleepFn = asyncio.sleep,
        clock: ClockFn = time.monotonic,
        startup_barrier: asyncio.Event | None = None,
    ) -> None:
        self.config = config
        self._sleep = sleep
        self._clock = clock
        self._startup_barrier = startup_barrier
        self._queue: asyncio.PriorityQueue[tuple[float, int, _QueueItem | None]] = (
            asyncio.PriorityQueue(maxsize=config.queue_size_limit)
        )
        self._global_semaphore = asyncio.Semaphore(config.global_concurrency_limit)
        self._category_semaphores: dict[str, asyncio.Semaphore] = {}
        self._workers: list[asyncio.Task[None]] = []
        self._sequence = count()
        self._closed = False
        self._closing = False
        self._started = False

    async def __aenter__(self) -> "PriorityScheduler":
        """Start the worker pool."""

        if self._started and self._workers:
            return self
        self._closed = False
        self._closing = False
        for index in range(self.config.worker_count):
            worker = asyncio.create_task(self._worker(), name=f"priority-scheduler-{index}")
            self._workers.append(worker)
        self._started = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Shut down the worker pool cleanly."""

        await self.close()

    async def close(self) -> None:
        """Drain the queue and stop all workers."""

        if self._closed:
            return
        self._closing = True
        if self._workers:
            alive_workers = [worker for worker in self._workers if not worker.done()]
            for _ in alive_workers:
                await self._queue.put((math.inf, next(self._sequence), None))
            await asyncio.gather(*self._workers, return_exceptions=True)
            while True:
                try:
                    _, _, queue_item = self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                else:
                    if queue_item is not None and not queue_item.future.done():
                        queue_item.future.cancel()
                    self._queue.task_done()
            self._workers = []
        self._closed = True
        self._closing = False
        self._started = False

    @property
    def is_closed(self) -> bool:
        """Return whether the scheduler has been closed."""

        return self._closed

    async def submit(self, job: TaskJob) -> TaskResult:
        """Validate and enqueue a job, then await its execution summary."""

        self._ensure_accepting_jobs()
        validated_job = TaskJob.model_validate(job)
        self._validate_job_against_config(validated_job)
        loop = asyncio.get_running_loop()
        future: asyncio.Future[TaskResult] = loop.create_future()
        queue_item = _QueueItem(job=validated_job, future=future)
        await self._queue.put((float(validated_job.priority), next(self._sequence), queue_item))
        return await future

    def enqueue(self, job: TaskJob) -> asyncio.Future[TaskResult]:
        """Enqueue a job and return the future that will receive its result."""

        self._ensure_accepting_jobs()
        validated_job = TaskJob.model_validate(job)
        self._validate_job_against_config(validated_job)
        loop = asyncio.get_running_loop()
        future: asyncio.Future[TaskResult] = loop.create_future()
        queue_item = _QueueItem(job=validated_job, future=future)
        self._queue.put_nowait((float(validated_job.priority), next(self._sequence), queue_item))
        return future

    def _ensure_accepting_jobs(self) -> None:
        if not self._started or self._closed or self._closing:
            raise RuntimeError("scheduler is closed")

    def _validate_job_against_config(self, job: TaskJob) -> None:
        if job.priority < self.config.priority_min or job.priority > self.config.priority_max:
            raise ValueError("job priority is outside the configured bounds")
        if job.max_retries is not None and job.max_retries > self.config.max_retries:
            raise ValueError("job retries are outside the configured bounds")
        effective_retries = self._effective_max_retries(job)
        if effective_retries < 0 or effective_retries > self.config.max_retries:
            raise ValueError("job retries are outside the configured bounds")
        effective_timeout = self._effective_timeout(job)
        if effective_timeout <= 0:
            raise ValueError("job timeout must be positive")
        self._category_limit(job.category)

    def _effective_max_retries(self, job: TaskJob) -> int:
        return self.config.max_retries if job.max_retries is None else min(job.max_retries, self.config.max_retries)

    def _effective_timeout(self, job: TaskJob) -> float:
        return self.config.default_timeout_seconds if job.timeout_seconds is None else job.timeout_seconds

    def _effective_backoff(self, job: TaskJob) -> float:
        return (
            self.config.default_retry_backoff_seconds
            if job.retry_backoff_seconds is None
            else job.retry_backoff_seconds
        )

    def _category_limit(self, category: str) -> int:
        return self.config.category_concurrency_limits.get(
            category,
            self.config.default_category_concurrency_limit,
        )

    def _category_semaphore(self, category: str) -> asyncio.Semaphore:
        semaphore = self._category_semaphores.get(category)
        if semaphore is None:
            semaphore = asyncio.Semaphore(self._category_limit(category))
            self._category_semaphores[category] = semaphore
        return semaphore

    async def _worker(self) -> None:
        if self._startup_barrier is not None:
            await self._startup_barrier.wait()
        try:
            while True:
                _, _, queue_item = await self._queue.get()
                try:
                    if queue_item is None:
                        return
                    await self._process_queue_item(queue_item)
                except asyncio.CancelledError:
                    if not queue_item.future.done():
                        queue_item.future.cancel()
                    raise
                finally:
                    self._queue.task_done()
        except asyncio.CancelledError:
            raise

    async def _process_queue_item(self, queue_item: _QueueItem) -> None:
        job = queue_item.job
        attempts = 0
        retries = self._effective_max_retries(job)
        backoff = self._effective_backoff(job)
        while True:
            attempts += 1
            started_at = self._clock()
            try:
                async with self._global_semaphore, self._category_semaphore(job.category):
                    result = await self._run_with_timeout(job)
            except asyncio.CancelledError:
                if not queue_item.future.done():
                    queue_item.future.cancel()
                raise
            except TaskTimeoutError as exc:
                summary = self._build_summary(
                    job=job,
                    attempts=attempts,
                    started_at=started_at,
                    finished_at=self._clock(),
                    status="timeout",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                exc.summary = summary
                if not queue_item.future.done():
                    queue_item.future.set_exception(exc)
                return
            except TaskExecutionError as exc:
                if not queue_item.future.done():
                    queue_item.future.set_exception(exc)
                return
            except Exception as exc:
                if attempts - 1 < retries:
                    await self._sleep(backoff)
                    backoff = min(
                        backoff * self.config.retry_backoff_multiplier,
                        self.config.max_retry_backoff_seconds,
                    )
                    continue
                summary = self._build_summary(
                    job=job,
                    attempts=attempts,
                    started_at=started_at,
                    finished_at=self._clock(),
                    status="error",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                error = TaskExecutionError(
                    f"task {job.job_id!r} failed after {attempts} attempt(s)",
                    summary=summary,
                )
                if not queue_item.future.done():
                    queue_item.future.set_exception(error)
                return
            else:
                finished_at = self._clock()
                summary = self._build_summary(
                    job=job,
                    attempts=attempts,
                    started_at=started_at,
                    finished_at=finished_at,
                    status="success",
                    result=result,
                )
                if not queue_item.future.done():
                    queue_item.future.set_result(summary)
                return

    async def _run_with_timeout(self, job: TaskJob) -> Any:
        timeout = self._effective_timeout(job)
        started_at = self._clock()
        inner = asyncio.create_task(self._invoke_handler(job))
        try:
            while True:
                if inner.done():
                    return inner.result()
                now = self._clock()
                if now - started_at >= timeout:
                    inner.cancel()
                    try:
                        await inner
                    except asyncio.CancelledError:
                        pass
                    raise TaskTimeoutError(
                        f"task {job.job_id!r} exceeded its {timeout} second timeout"
                    )
                remaining = timeout - (now - started_at)
                await self._sleep(min(remaining, self.config.timeout_poll_interval_seconds))
        except asyncio.CancelledError:
            inner.cancel()
            raise

    async def _invoke_handler(self, job: TaskJob) -> Any:
        result = job.handler(job)
        if inspect.isawaitable(result):
            return await result
        return result

    def _build_summary(
        self,
        *,
        job: TaskJob,
        attempts: int,
        started_at: float,
        finished_at: float,
        status: str,
        result: Any = None,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> TaskResult:
        return TaskResult.model_validate(
            {
                "job_id": job.job_id,
                "category": job.category,
                "priority": job.priority,
                "status": status,
                "attempts": attempts,
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_seconds": finished_at - started_at,
                "result": result,
                "error_type": error_type,
                "error_message": error_message,
            }
        )
