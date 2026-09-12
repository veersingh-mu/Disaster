"""Simulation Job Queue mechanism connecting FastAPI API to Worker.

### Architectural Decision:
For local development, automated CI testing, and hackathon demonstration, running an external
Redis broker or Celery worker cluster adds installation hurdles and infrastructure fragility.
Therefore, we provide:
1. `BaseJobQueue`: A clean, decoupled interface for enqueueing and consuming simulation runs.
2. `AsyncInMemoryJobQueue`: An asynchronous, zero-external-dependency queue using `asyncio.Queue`.
3. Clear extension point: For high-volume multi-node production deployment on Render/Railway/AWS,
   a `RedisJobQueue` or Celery task signature can drop in behind `BaseJobQueue` without altering
   any endpoint router or dependency code.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID


@dataclass
class SimulationJob:
    """Represents an enqueued simulation run task."""
    run_id: UUID
    scenario_id: UUID
    user_id: UUID
    mode: str = "full"
    request_id: Optional[str] = None
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseJobQueue(ABC):
    """Abstract interface for simulation job queues."""

    @abstractmethod
    async def enqueue(self, job: SimulationJob) -> None:
        """Place a simulation job onto the queue."""
        pass

    @abstractmethod
    async def dequeue(self, timeout: Optional[float] = None) -> Optional[SimulationJob]:
        """Retrieve and remove the next job from the queue, optionally waiting up to timeout seconds."""
        pass

    @abstractmethod
    def qsize(self) -> int:
        """Return the approximate number of pending jobs."""
        pass

    @abstractmethod
    def is_empty(self) -> bool:
        """Return True if no jobs are waiting."""
        pass


class AsyncInMemoryJobQueue(BaseJobQueue):
    """Thread-safe, asyncio-based in-memory queue for simulation jobs."""

    def __init__(self) -> None:
        self._queue: Optional[asyncio.Queue[SimulationJob]] = None

    def _get_queue(self) -> asyncio.Queue[SimulationJob]:
        if self._queue is None:
            self._queue = asyncio.Queue()
        return self._queue

    async def enqueue(self, job: SimulationJob) -> None:
        queue = self._get_queue()
        await queue.put(job)

    async def dequeue(self, timeout: Optional[float] = None) -> Optional[SimulationJob]:
        queue = self._get_queue()
        if timeout is None:
            return await queue.get()
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def task_done(self) -> None:
        if self._queue is not None:
            self._queue.task_done()

    def qsize(self) -> int:
        if self._queue is None:
            return 0
        return self._queue.qsize()

    def is_empty(self) -> bool:
        if self._queue is None:
            return True
        return self._queue.empty()


# Global singleton job queue
job_queue = AsyncInMemoryJobQueue()


def get_job_queue() -> BaseJobQueue:
    """Dependency provider for FastAPI routes or background workers."""
    return job_queue
