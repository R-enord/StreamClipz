"""Database-backed job queue with leases, retries and a dead-letter state.

Claiming a job gives its worker a lease that lasts `timeout_seconds`. The worker renews
the lease while it works (renew_lease). If the worker stops, crashes or runs too long, the
lease expires and the job can be claimed again. Each claim counts as one attempt. When the
attempts run out, the job is kept as "dead" for a person to look at.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from .clock import utcnow
from .models import Job

QUEUED = "queued"
RUNNING = "running"
SUCCEEDED = "succeeded"
DEAD = "dead"

MAX_ERROR_CHARS = 4000


def retry_delay(attempts: int) -> timedelta:
    """30 seconds after the first failure, then 60, 120 and so on, capped at 5 minutes."""
    return timedelta(seconds=min(300, 30 * 2 ** max(0, attempts - 1)))


def _claimable(now: datetime):
    return or_(
        and_(Job.status == QUEUED, Job.run_after <= now),
        and_(Job.status == RUNNING, Job.lease_expires_at < now),
    )


def enqueue(
    db: Session,
    kind: str,
    payload: dict[str, Any] | None = None,
    *,
    max_attempts: int = 3,
    timeout_seconds: int = 600,
    run_after: datetime | None = None,
    now: datetime | None = None,
) -> int:
    if max_attempts < 1 or timeout_seconds < 1:
        raise ValueError("max_attempts and timeout_seconds must be at least 1")
    now = now or utcnow()
    job = Job(
        kind=kind,
        payload=json.dumps(payload or {}),
        status=QUEUED,
        attempts=0,
        max_attempts=max_attempts,
        timeout_seconds=timeout_seconds,
        run_after=run_after or now,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.commit()
    return job.id


def _retire_abandoned_jobs(db: Session, now: datetime) -> None:
    """A job whose lease ran out on its last attempt is dead. It is not retried forever."""
    db.execute(
        update(Job)
        .where(Job.status == RUNNING, Job.lease_expires_at < now, Job.attempts >= Job.max_attempts)
        .values(
            status=DEAD,
            lease_owner=None,
            lease_expires_at=None,
            finished_at=now,
            updated_at=now,
            last_error=func.coalesce(Job.last_error, "lease expired after the last attempt"),
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()


def claim_next(db: Session, worker_id: str, *, now: datetime | None = None) -> Job | None:
    """Take the next job that is due, or return None. The claim is atomic."""
    now = now or utcnow()
    _retire_abandoned_jobs(db, now)
    for _ in range(10):  # another worker may take the candidate between our read and our write
        candidate = db.execute(
            select(Job.id, Job.timeout_seconds)
            .where(_claimable(now))
            .order_by(Job.run_after, Job.id)
            .limit(1)
        ).first()
        if candidate is None:
            db.rollback()
            return None
        job_id, timeout_seconds = candidate
        result = db.execute(
            update(Job)
            .where(Job.id == job_id, _claimable(now))
            .values(
                status=RUNNING,
                lease_owner=worker_id,
                lease_expires_at=now + timedelta(seconds=timeout_seconds),
                attempts=Job.attempts + 1,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        db.commit()
        if result.rowcount == 1:
            return db.get(Job, job_id, populate_existing=True)
    return None


def renew_lease(
    db: Session, job_id: int, worker_id: str, timeout_seconds: int, *, now: datetime | None = None
) -> bool:
    """Extend the lease. Returns False if this worker no longer holds the job."""
    now = now or utcnow()
    result = db.execute(
        update(Job)
        .where(Job.id == job_id, Job.status == RUNNING, Job.lease_owner == worker_id)
        .values(lease_expires_at=now + timedelta(seconds=timeout_seconds), updated_at=now)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount == 1


def complete(db: Session, job_id: int, worker_id: str, *, now: datetime | None = None) -> bool:
    """Mark the job as succeeded. Returns False if this worker no longer holds the job."""
    now = now or utcnow()
    result = db.execute(
        update(Job)
        .where(Job.id == job_id, Job.status == RUNNING, Job.lease_owner == worker_id)
        .values(
            status=SUCCEEDED,
            lease_owner=None,
            lease_expires_at=None,
            last_error=None,
            finished_at=now,
            updated_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount == 1


def fail(
    db: Session,
    job_id: int,
    worker_id: str,
    error: str,
    *,
    now: datetime | None = None,
    dead: bool = False,
) -> str | None:
    """Record a failed attempt. Returns the new status, or None if this worker no longer holds the job.

    The job goes back to the queue after a delay, or to dead when no attempts are left
    (or when `dead` is True, for errors that retrying cannot fix).
    """
    now = now or utcnow()
    current = db.execute(
        select(Job.attempts, Job.max_attempts).where(
            Job.id == job_id, Job.status == RUNNING, Job.lease_owner == worker_id
        )
    ).first()
    if current is None:
        db.rollback()
        return None
    attempts, max_attempts = current
    if dead or attempts >= max_attempts:
        new_status, run_after = DEAD, now
    else:
        new_status, run_after = QUEUED, now + retry_delay(attempts)
    result = db.execute(
        update(Job)
        .where(
            Job.id == job_id,
            Job.status == RUNNING,
            Job.lease_owner == worker_id,
            Job.attempts == attempts,
        )
        .values(
            status=new_status,
            run_after=run_after,
            lease_owner=None,
            lease_expires_at=None,
            last_error=error[:MAX_ERROR_CHARS],
            finished_at=now if new_status == DEAD else None,
            updated_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return new_status if result.rowcount == 1 else None
