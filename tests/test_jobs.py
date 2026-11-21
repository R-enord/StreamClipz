"""Job queue rules: claims, leases, retries and dead-letter. Uses a fake clock, so no sleeping."""

from datetime import datetime, timedelta

import pytest

from core import jobs
from core.db import make_engine, make_session_factory, migrate
from core.models import Job

START = datetime(2026, 11, 21, 12, 0, 0)


class FakeClock:
    def __init__(self, start):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


@pytest.fixture()
def clock():
    return FakeClock(START)


@pytest.fixture()
def engine(tmp_path):
    path = tmp_path / "jobs.db"
    migrate(path)
    eng = make_engine(path)
    yield eng
    eng.dispose()


@pytest.fixture()
def sessions(engine):
    return make_session_factory(engine)


def read_job(sessions, job_id) -> Job:
    with sessions() as db:
        return db.get(Job, job_id)


def test_claim_is_exclusive_while_the_lease_is_active(sessions, clock):
    with sessions() as db:
        job_id = jobs.enqueue(db, "demo", timeout_seconds=60, now=clock())
    with sessions() as db:
        first = jobs.claim_next(db, "A", now=clock())
    with sessions() as db:
        second = jobs.claim_next(db, "B", now=clock())
    assert first.id == job_id and first.lease_owner == "A" and first.attempts == 1
    assert second is None


def test_job_waits_until_run_after(sessions, clock):
    with sessions() as db:
        jobs.enqueue(db, "later", run_after=START + timedelta(seconds=60), now=clock())
    with sessions() as db:
        assert jobs.claim_next(db, "A", now=clock()) is None
    clock.advance(60)
    with sessions() as db:
        assert jobs.claim_next(db, "A", now=clock()) is not None


def test_expired_lease_is_reclaimed_and_counts_as_an_attempt(sessions, clock):
    with sessions() as db:
        job_id = jobs.enqueue(db, "demo", timeout_seconds=60, now=clock())
    with sessions() as db:
        jobs.claim_next(db, "A", now=clock())  # worker A disappears
    clock.advance(30)
    with sessions() as db:
        assert jobs.claim_next(db, "B", now=clock()) is None
    clock.advance(31)
    with sessions() as db:
        taken = jobs.claim_next(db, "B", now=clock())
    assert taken.id == job_id and taken.lease_owner == "B" and taken.attempts == 2


def test_renewed_lease_is_not_reclaimed(sessions, clock):
    with sessions() as db:
        job_id = jobs.enqueue(db, "demo", timeout_seconds=60, now=clock())
    with sessions() as db:
        jobs.claim_next(db, "A", now=clock())
    clock.advance(50)
    with sessions() as db:
        assert jobs.renew_lease(db, job_id, "A", 60, now=clock())  # lease now runs to +110 s
    clock.advance(50)  # +100 s
    with sessions() as db:
        assert jobs.claim_next(db, "B", now=clock()) is None
    clock.advance(11)  # +111 s
    with sessions() as db:
        assert jobs.claim_next(db, "B", now=clock()) is not None


def test_only_the_lease_owner_can_complete_or_fail(sessions, clock):
    with sessions() as db:
        job_id = jobs.enqueue(db, "demo", timeout_seconds=60, now=clock())
    with sessions() as db:
        jobs.claim_next(db, "A", now=clock())
    clock.advance(61)
    with sessions() as db:
        jobs.claim_next(db, "B", now=clock())  # B takes over after A's lease ran out
    with sessions() as db:
        assert jobs.complete(db, job_id, "A", now=clock()) is False
    with sessions() as db:
        assert jobs.fail(db, job_id, "A", "late report", now=clock()) is None
    with sessions() as db:
        assert jobs.complete(db, job_id, "B", now=clock()) is True
    assert read_job(sessions, job_id).status == "succeeded"


def test_failures_back_off_then_die_after_the_last_attempt(sessions, clock):
    with sessions() as db:
        job_id = jobs.enqueue(db, "demo", max_attempts=2, now=clock())
    with sessions() as db:
        jobs.claim_next(db, "A", now=clock())
    with sessions() as db:
        assert jobs.fail(db, job_id, "A", "boom", now=clock()) == "queued"
    with sessions() as db:
        assert jobs.claim_next(db, "A", now=clock()) is None  # still backing off
    clock.advance(30)
    with sessions() as db:
        assert jobs.claim_next(db, "A", now=clock()).attempts == 2
    with sessions() as db:
        assert jobs.fail(db, job_id, "A", "boom again", now=clock()) == "dead"
    clock.advance(3600)
    with sessions() as db:
        assert jobs.claim_next(db, "A", now=clock()) is None  # dead jobs are never picked up again


def test_abandoned_job_on_its_last_attempt_becomes_dead(sessions, clock):
    with sessions() as db:
        job_id = jobs.enqueue(db, "demo", max_attempts=1, timeout_seconds=60, now=clock())
    with sessions() as db:
        jobs.claim_next(db, "A", now=clock())  # A vanishes
    clock.advance(61)
    with sessions() as db:
        assert jobs.claim_next(db, "B", now=clock()) is None
    row = read_job(sessions, job_id)
    assert row.status == "dead" and "lease expired" in row.last_error


def test_retry_delay_grows_and_is_capped():
    assert jobs.retry_delay(1) == timedelta(seconds=30)
    assert jobs.retry_delay(2) == timedelta(seconds=60)
    assert jobs.retry_delay(10) == timedelta(seconds=300)


def test_enqueue_rejects_nonsense_limits(sessions, clock):
    with sessions() as db, pytest.raises(ValueError):
        jobs.enqueue(db, "demo", max_attempts=0, now=clock())
