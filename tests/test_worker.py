"""Worker behaviour: retries after a failure, survival across restarts, timeouts and heartbeats."""

from datetime import datetime, timedelta

import pytest

from core import jobs
from core.db import make_engine, make_session_factory, migrate
from core.models import Job
from core.worker import Worker

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
def db_path(tmp_path):
    path = tmp_path / "worker.db"
    migrate(path)
    return path


@pytest.fixture()
def engine(db_path):
    eng = make_engine(db_path)
    yield eng
    eng.dispose()


@pytest.fixture()
def sessions(engine):
    return make_session_factory(engine)


def read_job(sessions, job_id) -> Job:
    with sessions() as db:
        return db.get(Job, job_id)


def test_failed_job_is_retried_once_and_then_succeeds(sessions, clock):
    calls = []

    def flaky(ctx):
        calls.append(ctx.attempt)
        if len(calls) == 1:
            raise RuntimeError("simulated failure")

    with sessions() as db:
        job_id = jobs.enqueue(db, "demo", {"x": 1}, max_attempts=3, now=clock())
    worker = Worker(sessions, worker_id="w1", clock=clock)
    worker.register("demo", flaky)

    assert worker.run_once() is True  # first attempt fails
    assert read_job(sessions, job_id).status == "queued"
    assert worker.run_once() is False  # the retry waits for its backoff
    clock.advance(31)
    assert worker.run_once() is True  # second attempt succeeds

    row = read_job(sessions, job_id)
    assert row.status == "succeeded" and row.attempts == 2 and row.last_error is None
    assert calls == [1, 2]


def test_job_survives_a_restart_and_finishes_after_its_lease_expires(db_path, clock):
    engine_a = make_engine(db_path)
    sessions_a = make_session_factory(engine_a)
    with sessions_a() as db:
        job_id = jobs.enqueue(db, "demo", {"n": 7}, timeout_seconds=60, now=clock())
    with sessions_a() as db:
        claimed = jobs.claim_next(db, "worker-a", now=clock())  # worker A takes the job, then dies
    assert claimed.id == job_id
    engine_a.dispose()  # the process goes away

    engine_b = make_engine(db_path)
    sessions_b = make_session_factory(engine_b)
    seen = []
    worker_b = Worker(sessions_b, worker_id="worker-b", clock=clock)
    worker_b.register("demo", lambda ctx: seen.append(ctx.payload))
    assert worker_b.run_until_idle() == 0  # the lease is still active
    clock.advance(61)
    assert worker_b.run_until_idle() == 1

    row = read_job(sessions_b, job_id)
    assert seen == [{"n": 7}]
    assert row.status == "succeeded" and row.attempts == 2
    engine_b.dispose()


def test_handler_that_runs_past_its_timeout_is_retried(sessions, clock):
    def slow_then_fine(ctx):
        if ctx.attempt == 1:
            clock.advance(120)  # longer than the 60 s lease
            ctx.ensure_time()  # raises JobTimeout

    with sessions() as db:
        job_id = jobs.enqueue(db, "slow", timeout_seconds=60, now=clock())
    worker = Worker(sessions, worker_id="w1", clock=clock)
    worker.register("slow", slow_then_fine)

    worker.run_once()
    row = read_job(sessions, job_id)
    assert row.status == "queued" and "timed out" in row.last_error

    clock.advance(31)
    worker.run_once()
    row = read_job(sessions, job_id)
    assert row.status == "succeeded" and row.attempts == 2 and row.last_error is None


def test_heartbeat_keeps_a_long_job_alive(sessions, clock):
    def long_job(ctx):
        for _ in range(3):
            clock.advance(40)  # 120 s in total, twice the lease
            ctx.heartbeat()

    with sessions() as db:
        job_id = jobs.enqueue(db, "long", timeout_seconds=60, now=clock())
    worker = Worker(sessions, worker_id="w1", clock=clock)
    worker.register("long", long_job)

    worker.run_once()
    assert read_job(sessions, job_id).status == "succeeded"


def test_unknown_job_kind_goes_straight_to_dead(sessions, clock):
    with sessions() as db:
        job_id = jobs.enqueue(db, "nobody-handles-this", now=clock())
    worker = Worker(sessions, worker_id="w1", clock=clock)

    worker.run_once()
    row = read_job(sessions, job_id)
    assert row.status == "dead" and "no handler" in row.last_error


def test_error_on_the_last_attempt_is_kept_as_dead(sessions, clock):
    def broken(ctx):
        raise ValueError("boom")

    with sessions() as db:
        job_id = jobs.enqueue(db, "broken", max_attempts=1, now=clock())
    worker = Worker(sessions, worker_id="w1", clock=clock)
    worker.register("broken", broken)

    worker.run_once()
    row = read_job(sessions, job_id)
    assert row.status == "dead" and "boom" in row.last_error
    clock.advance(3600)
    assert worker.run_once() is False


def test_duplicate_handler_registration_is_refused(sessions):
    worker = Worker(sessions, worker_id="w1")
    worker.register("demo", lambda ctx: None)
    with pytest.raises(ValueError):
        worker.register("demo", lambda ctx: None)
