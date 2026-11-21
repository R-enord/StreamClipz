# ADR 0002: Database migrations and the job queue

Status: accepted (2026-11-21)

## Context

The first version created its tables by hand, and nothing recorded schema changes. Background
work (recording, cutting, rendering, publishing checks) needs a queue that survives crashes
and restarts, without adding a separate service yet.

## Decision

1. **Alembic owns the schema.** Every change is a numbered migration in `core/migrations`. The
   app upgrades the database when it starts. Migrations never import the application models, so
   an old migration still runs the same way after the models change.
2. **The first migration adopts the existing database.** It uses `IF NOT EXISTS` and only changes
   what is needed (a primary key on `login_failures`, which the old table lacked). The test suite
   upgrades a copy of the old schema with real data and checks that the data survives.
3. **Jobs live in the database.** A job is claimed with a lease. The worker renews the lease while
   it works. An expired lease can be claimed again, and each claim counts as an attempt. Failed
   jobs retry with a delay (30 s, 60 s, ... up to 5 min) and end as `dead` when attempts run out.
4. **Claims are atomic.** A claim is one conditional update. Two workers cannot both win a job.
5. **Handlers must be safe to repeat.** A job can run twice if its worker loses the lease.

## Consequences

- No extra service to run. SQLite is enough for one owner. Moving to PostgreSQL later changes the
  engine URL and reuses the same migrations and models.
- A job that is stuck on a dead worker waits for its lease to expire before it runs again.
  Lease length (`timeout_seconds`) is the trade-off between fast recovery and false timeouts.
- Handlers must check `ctx.ensure_time()` or call `ctx.heartbeat()` during long steps.
