"""Job queue table, used by the background worker.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-21
"""

from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id               INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            kind             VARCHAR(100) NOT NULL,
            payload          TEXT NOT NULL,
            status           VARCHAR(20) NOT NULL,
            attempts         INTEGER NOT NULL,
            max_attempts     INTEGER NOT NULL,
            timeout_seconds  INTEGER NOT NULL,
            run_after        DATETIME NOT NULL,
            lease_owner      VARCHAR(64),
            lease_expires_at DATETIME,
            last_error       TEXT,
            created_at       DATETIME NOT NULL,
            updated_at       DATETIME NOT NULL,
            finished_at      DATETIME
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS jobs_claim ON jobs (status, run_after)")
    op.execute("CREATE INDEX IF NOT EXISTS jobs_lease ON jobs (lease_expires_at)")


def downgrade() -> None:
    # Dropping the table also drops any queued work, so downgrade only after stopping the worker.
    op.execute("DROP INDEX IF EXISTS jobs_lease")
    op.execute("DROP INDEX IF EXISTS jobs_claim")
    op.execute("DROP TABLE IF EXISTS jobs")
