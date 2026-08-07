from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

CODING_DIR = Path(__file__).resolve().parents[1] / "Coding"
if str(CODING_DIR) not in sys.path:
    sys.path.insert(0, str(CODING_DIR))

from exceptions import TaskExecutionError, TaskTimeoutError
from scheduler import PriorityScheduler
from schemas import SchedulerConfig, TaskJob, TaskResult


class ManualClock:
    def __init__(self) -> None:
        self.value = 0.0

    def now(self) -> float:
        return self.value

    async def sleep(self, seconds: float) -> None:
        self.value += seconds
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_priority_ordering_respects_priority_then_fifo() -> None:
    start_event = asyncio.Event()
    execution_order: list[str] = []

    async def handler(job: TaskJob) -> str:
        execution_order.append(job.job_id)
        return job.job_id

    scheduler = PriorityScheduler(
        SchedulerConfig(
            worker_count=1,
            global_concurrency_limit=1,
            queue_size_limit=10,
            max_retries=0,
            default_timeout_seconds=1.0,
            default_category_concurrency_limit=1,
        ),
        startup_barrier=start_event,
    )

    async with scheduler:
        futures = [
            scheduler.enqueue(
                TaskJob(job_id="low", category="alpha", priority=9, handler=handler)
            ),
            scheduler.enqueue(
                TaskJob(job_id="high-first", category="alpha", priority=1, handler=handler)
            ),
            scheduler.enqueue(
                TaskJob(job_id="high-second", category="alpha", priority=1, handler=handler)
            ),
            scheduler.enqueue(
                TaskJob(job_id="mid", category="alpha", priority=4, handler=handler)
            ),
        ]
        start_event.set()
        results = await asyncio.gather(*futures)

    assert execution_order == ["high-first", "high-second", "mid", "low"]
    assert {result.job_id for result in results} == set(execution_order)
    assert [result.priority for result in results] == [9, 1, 1, 4]


@pytest.mark.asyncio
async def test_concurrency_throttling_enforces_global_and_category_limits() -> None:
    start_event = asyncio.Event()
    release_event = asyncio.Event()
    lock = asyncio.Lock()
    active_global = 0
    max_global = 0
    active_by_category = {"alpha": 0, "beta": 0}
    max_by_category = {"alpha": 0, "beta": 0}
    first_two_started = asyncio.Event()

    async def handler(job: TaskJob) -> str:
        nonlocal active_global, max_global
        async with lock:
            active_global += 1
            active_by_category[job.category] += 1
            max_global = max(max_global, active_global)
            max_by_category[job.category] = max(max_by_category[job.category], active_by_category[job.category])
            if active_global == 2:
                first_two_started.set()
        await release_event.wait()
        async with lock:
            active_global -= 1
            active_by_category[job.category] -= 1
        return job.job_id

    scheduler = PriorityScheduler(
        SchedulerConfig(
            worker_count=3,
            global_concurrency_limit=2,
            queue_size_limit=10,
            max_retries=0,
            default_timeout_seconds=1.0,
            default_category_concurrency_limit=1,
            category_concurrency_limits={"alpha": 1, "beta": 1},
        ),
        startup_barrier=start_event,
    )

    async with scheduler:
        futures = [
            scheduler.enqueue(TaskJob(job_id="alpha-1", category="alpha", priority=1, handler=handler)),
            scheduler.enqueue(TaskJob(job_id="alpha-2", category="alpha", priority=2, handler=handler)),
            scheduler.enqueue(TaskJob(job_id="beta-1", category="beta", priority=1, handler=handler)),
        ]
        start_event.set()
        await asyncio.wait_for(first_two_started.wait(), timeout=1.0)
        release_event.set()
        results = await asyncio.gather(*futures)

    assert max_global == 2
    assert max_by_category["alpha"] == 1
    assert max_by_category["beta"] == 1
    assert {result.job_id for result in results} == {"alpha-1", "alpha-2", "beta-1"}


@pytest.mark.asyncio
async def test_retry_exhaustion_raises_task_execution_error() -> None:
    attempts = 0
    start_event = asyncio.Event()

    async def handler(job: TaskJob) -> str:
        nonlocal attempts
        attempts += 1
        raise ValueError("transient failure")

    scheduler = PriorityScheduler(
        SchedulerConfig(
            worker_count=1,
            global_concurrency_limit=1,
            queue_size_limit=10,
            max_retries=2,
            default_timeout_seconds=1.0,
            default_retry_backoff_seconds=0.0,
            timeout_poll_interval_seconds=0.01,
            default_category_concurrency_limit=1,
        ),
        sleep=lambda _: asyncio.sleep(0),
        startup_barrier=start_event,
    )

    async with scheduler:
        start_event.set()
        with pytest.raises(TaskExecutionError) as exc_info:
            await scheduler.submit(
                TaskJob(job_id="retry-me", category="alpha", priority=1, handler=handler)
            )

    assert attempts == 3
    assert exc_info.value.summary is not None
    assert exc_info.value.summary.attempts == 3
    assert exc_info.value.summary.status == "error"


@pytest.mark.asyncio
async def test_timeout_enforcement_uses_injectable_clock_and_sleep() -> None:
    clock = ManualClock()
    start_event = asyncio.Event()
    release_event = asyncio.Event()

    async def handler(job: TaskJob) -> str:
        await release_event.wait()
        return "never"

    scheduler = PriorityScheduler(
        SchedulerConfig(
            worker_count=1,
            global_concurrency_limit=1,
            queue_size_limit=10,
            max_retries=0,
            default_timeout_seconds=1.0,
            timeout_poll_interval_seconds=0.25,
            default_category_concurrency_limit=1,
        ),
        sleep=clock.sleep,
        clock=clock.now,
        startup_barrier=start_event,
    )

    async with scheduler:
        start_event.set()
        with pytest.raises(TaskTimeoutError) as exc_info:
            await scheduler.submit(
                TaskJob(
                    job_id="timeout",
                    category="alpha",
                    priority=1,
                    handler=handler,
                    timeout_seconds=1.0,
                )
            )

    assert exc_info.value.summary is not None
    assert exc_info.value.summary.status == "timeout"
    assert exc_info.value.summary.attempts == 1


@pytest.mark.asyncio
async def test_cancellation_safety_preserves_cancelled_error() -> None:
    async def handler(job: TaskJob) -> str:
        raise asyncio.CancelledError

    scheduler = PriorityScheduler(
        SchedulerConfig(
            worker_count=1,
            global_concurrency_limit=1,
            queue_size_limit=10,
            max_retries=0,
            default_timeout_seconds=1.0,
            default_category_concurrency_limit=1,
        )
    )

    async with scheduler:
        with pytest.raises(asyncio.CancelledError):
            await scheduler.submit(
                TaskJob(job_id="cancelled", category="alpha", priority=1, handler=handler)
            )


@pytest.mark.asyncio
async def test_worker_cancellation_propagates_and_cancels_pending_future() -> None:
    start_event = asyncio.Event()
    handler_started = asyncio.Event()
    release_event = asyncio.Event()

    async def handler(job: TaskJob) -> str:
        handler_started.set()
        await release_event.wait()
        return job.job_id

    scheduler = PriorityScheduler(
        SchedulerConfig(
            worker_count=1,
            global_concurrency_limit=1,
            queue_size_limit=10,
            max_retries=0,
            default_timeout_seconds=1.0,
            default_category_concurrency_limit=1,
        ),
        startup_barrier=start_event,
    )

    async with scheduler:
        worker = scheduler._workers[0]
        future = scheduler.enqueue(
            TaskJob(job_id="worker-cancel", category="alpha", priority=1, handler=handler)
        )
        start_event.set()
        await asyncio.wait_for(handler_started.wait(), timeout=1.0)
        worker.cancel()

        with pytest.raises(asyncio.CancelledError):
            await worker

        await asyncio.sleep(0)

        assert future.cancelled()
        with pytest.raises(asyncio.CancelledError):
            await future

    assert worker.done()
    assert worker.cancelled()


@pytest.mark.asyncio
async def test_cancelled_job_terminates_worker_task() -> None:
    start_event = asyncio.Event()

    async def handler(job: TaskJob) -> str:
        raise asyncio.CancelledError

    scheduler = PriorityScheduler(
        SchedulerConfig(
            worker_count=1,
            global_concurrency_limit=1,
            queue_size_limit=10,
            max_retries=0,
            default_timeout_seconds=1.0,
            default_category_concurrency_limit=1,
        ),
        startup_barrier=start_event,
    )

    async with scheduler:
        worker = scheduler._workers[0]
        start_event.set()
        with pytest.raises(asyncio.CancelledError):
            await scheduler.submit(
                TaskJob(job_id="cancelled-worker", category="alpha", priority=1, handler=handler)
            )
        await asyncio.sleep(0)

    assert worker.done()
    assert worker.cancelled()


@pytest.mark.asyncio
async def test_queue_size_limit_is_enforced() -> None:
    start_event = asyncio.Event()
    release_event = asyncio.Event()

    async def handler(job: TaskJob) -> str:
        await release_event.wait()
        return job.job_id

    scheduler = PriorityScheduler(
        SchedulerConfig(
            worker_count=1,
            global_concurrency_limit=1,
            queue_size_limit=1,
            max_retries=0,
            default_timeout_seconds=1.0,
            default_category_concurrency_limit=1,
        ),
        startup_barrier=start_event,
    )

    async with scheduler:
        start_event.set()
        first_future = scheduler.enqueue(
            TaskJob(job_id="queued-1", category="alpha", priority=1, handler=handler)
        )

        with pytest.raises(asyncio.QueueFull):
            scheduler.enqueue(
                TaskJob(job_id="queued-2", category="alpha", priority=2, handler=handler)
            )

        release_event.set()
        result = await first_future

    assert result.job_id == "queued-1"


@pytest.mark.asyncio
async def test_context_manager_cleans_up_workers() -> None:
    start_event = asyncio.Event()

    async def handler(job: TaskJob) -> str:
        return job.job_id

    scheduler = PriorityScheduler(
        SchedulerConfig(
            worker_count=2,
            global_concurrency_limit=2,
            queue_size_limit=10,
            max_retries=0,
            default_timeout_seconds=1.0,
            default_category_concurrency_limit=1,
        ),
        startup_barrier=start_event,
    )

    async with scheduler:
        start_event.set()
        result = await scheduler.submit(
            TaskJob(job_id="cleanup", category="alpha", priority=1, handler=handler)
        )
        assert result == TaskResult.model_validate(result.model_dump())

    assert scheduler.is_closed
    assert all(worker.done() for worker in scheduler._workers)
    assert scheduler._queue.empty()


@pytest.mark.asyncio
async def test_submit_before_enter_is_rejected() -> None:
    scheduler = PriorityScheduler(
        SchedulerConfig(
            worker_count=1,
            global_concurrency_limit=1,
            queue_size_limit=10,
            max_retries=0,
            default_timeout_seconds=1.0,
            default_category_concurrency_limit=1,
        )
    )

    with pytest.raises(RuntimeError, match="scheduler is closed"):
        await scheduler.submit(
            TaskJob(
                job_id="not-started",
                category="alpha",
                priority=1,
                handler=lambda job: job.job_id,
            )
        )


def test_job_retry_limits_must_not_exceed_scheduler_config() -> None:
    scheduler = PriorityScheduler(
        SchedulerConfig(
            worker_count=1,
            global_concurrency_limit=1,
            queue_size_limit=10,
            max_retries=1,
            default_timeout_seconds=1.0,
            default_category_concurrency_limit=1,
        )
    )

    with pytest.raises(ValueError, match="job retries are outside the configured bounds"):
        scheduler._validate_job_against_config(
            TaskJob(
                job_id="retry-bounds",
                category="alpha",
                priority=1,
                handler=lambda job: job.job_id,
                max_retries=2,
            )
        )


def test_schema_validation_rejects_invalid_configuration_and_jobs() -> None:
    with pytest.raises(ValidationError):
        SchedulerConfig(
            worker_count=1,
            global_concurrency_limit=1,
            queue_size_limit=0,
            max_retries=0,
            default_timeout_seconds=1.0,
            default_category_concurrency_limit=1,
        )

    with pytest.raises(ValidationError):
        TaskJob(
            job_id="",
            category="alpha",
            priority=101,
            handler=lambda job: job.job_id,
        )

    result = TaskResult.model_validate(
        {
            "job_id": "job",
            "category": "alpha",
            "priority": 1,
            "status": "success",
            "attempts": 1,
            "started_at": 1.0,
            "finished_at": 2.0,
            "duration_seconds": 1.0,
            "result": "ok",
        }
    )
    assert result.status == "success"
