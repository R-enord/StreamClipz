"""Worker: claims jobs, runs their handlers and records the outcome.

A handler is a plain function that receives a JobContext. A job can run more than once (if
its worker loses the lease), so handlers should be safe to repeat.
"""

from __future__ import annotations

import functools
import json
import logging
import threading
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import sessionmaker

from . import jobs
from .clock import utcnow

log = logging.getLogger("streamclipz.worker")


class JobTimeout(Exception):
    """The job ran past its lease, or another worker took it. The queue will retry it."""


class UnknownJobKind(Exception):
    """No handler is registered for the job's kind. Retrying cannot help."""


class JobContext:
    """What a handler receives: the job's data, plus heartbeat() and ensure_time() for long work."""

    def __init__(
        self,
        *,
        job_id: int,
        kind: str,
        payload: dict[str, Any],
        attempt: int,
        lease_until: datetime,
        timeout_seconds: int,
        renew: Callable[[], bool],
        clock: Callable[[], datetime],
    ) -> None:
        self.job_id = job_id
        self.kind = kind
        self.payload = payload
        self.attempt = attempt
        self.lease_until = lease_until
        self._timeout_seconds = timeout_seconds
        self._renew = renew
        self._clock = clock

    def ensure_time(self) -> None:
        """Raise JobTimeout once the job has run past its lease. Call between steps of long work."""
        if self._clock() >= self.lease_until:
            raise JobTimeout(f"ran past its {self._timeout_seconds} second limit")

    def heartbeat(self) -> None:
        """Renew the lease. Call this regularly during long work."""
        self.ensure_time()
        if not self._renew():
            raise JobTimeout("another worker took the job")
        self.lease_until = self._clock() + timedelta(seconds=self._timeout_seconds)


Handler = Callable[[JobContext], None]


class Worker:
    def __init__(
        self,
        session_factory: sessionmaker,
        *,
        worker_id: str | None = None,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._sessions = session_factory
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self._clock = clock
        self._handlers: dict[str, Handler] = {}

    def register(self, kind: str, handler: Handler) -> None:
        if kind in self._handlers:
            raise ValueError(f"A handler is already registered for {kind!r}")
        self._handlers[kind] = handler

    def run_once(self) -> bool:
        """Run at most one job. Returns False when nothing was due."""
        with self._sessions() as db:
            job = jobs.claim_next(db, self.worker_id, now=self._clock())
            if job is None:
                return False
            job_id = job.id
            kind = job.kind
            payload_text = job.payload
            attempt = job.attempts
            lease_until = job.lease_expires_at
            timeout_seconds = job.timeout_seconds

        try:
            handler = self._handlers.get(kind)
            if handler is None:
                raise UnknownJobKind(f"no handler for job kind {kind!r}")
            context = JobContext(
                job_id=job_id,
                kind=kind,
                payload=json.loads(payload_text or "{}"),
                attempt=attempt,
                lease_until=lease_until,
                timeout_seconds=timeout_seconds,
                renew=functools.partial(self._renew, job_id, timeout_seconds),
                clock=self._clock,
            )
            handler(context)
        except UnknownJobKind as exc:
            log.error("job %s: %s", job_id, exc)
            self._record_failure(job_id, str(exc), dead=True)
        except JobTimeout as exc:
            log.warning("job %s (%s) timed out: %s", job_id, kind, exc)
            self._record_failure(job_id, f"timed out: {exc}")
        except Exception as exc:  # any handler error is recorded, then retried or dead-lettered
            log.exception("job %s (%s) failed", job_id, kind)
            self._record_failure(job_id, f"{type(exc).__name__}: {exc}")
        else:
            self._record_success(job_id)
        return True

    def run_until_idle(self, max_jobs: int | None = None) -> int:
        """Run jobs until none are due (or max_jobs were run). Returns how many ran."""
        processed = 0
        while max_jobs is None or processed < max_jobs:
            if not self.run_once():
                break
            processed += 1
        return processed

    def run_forever(self, stop: threading.Event | None = None, idle_seconds: float = 5.0) -> None:
        stop = stop or threading.Event()
        while not stop.is_set():
            if not self.run_once():
                stop.wait(idle_seconds)

    def _renew(self, job_id: int, timeout_seconds: int) -> bool:
        with self._sessions() as db:
            return jobs.renew_lease(db, job_id, self.worker_id, timeout_seconds, now=self._clock())

    def _record_success(self, job_id: int) -> None:
        with self._sessions() as db:
            if not jobs.complete(db, job_id, self.worker_id, now=self._clock()):
                log.warning("job %s finished after its lease was lost; it is owned by another worker", job_id)

    def _record_failure(self, job_id: int, message: str, *, dead: bool = False) -> None:
        with self._sessions() as db:
            status = jobs.fail(db, job_id, self.worker_id, message, now=self._clock(), dead=dead)
        if status is None:
            log.warning("job %s failed after its lease was lost; it is owned by another worker", job_id)
