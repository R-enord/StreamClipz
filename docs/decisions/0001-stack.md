# ADR 0001: Technology stack

Status: accepted (2026-11-21)

## Context

We need a stack that one person can run on a laptop today, that can move to a server
later without a rewrite, that costs nothing to start, and that has mature tooling.

## Decision

- **Python 3.12.** Already installed on the laptop.
- **FastAPI** for the web app and API. Already in use.
- **SQLAlchemy 2** for database access and **Alembic** for schema migrations. Replaces hand-written SQL.
- **SQLite** (WAL mode) now. **PostgreSQL** when the system is hosted.
- **pydantic-settings** for configuration. Secrets come from the environment or the operating
  system, never from git.
- **Background work** through a database-backed job table with leases, retries and timeouts.
  A separate queue service only when the job table is no longer enough.
- **ffmpeg** for media, called through one wrapper that enforces timeouts and logs output.
- **pytest** for tests, **ruff** for linting and formatting, **GitHub Actions** for CI,
  **Dependabot** for dependency updates.

## Consequences

- Free to run, and simple to back up (one database file plus the media folders).
- SQLite allows one writer at a time. That is fine for one owner; the move to PostgreSQL is a planned step.
- The job table needs focused tests (crash during a job, duplicate workers, retries).
- Choosing Python for media work means ffmpeg must be installed on each machine. The runbook covers it.
