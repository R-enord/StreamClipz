"""Baseline: accounts, sign-in sessions and failed-login counts.

These tables match what the first version of the app created by hand. Every statement is
safe to run on a database that already has the tables, so existing data is kept. The one
change is that login_failures gets an id column, because the old table had no primary key.

Revision ID: 0001
Revises:
Create Date: 2026-11-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

CREATE_LOGIN_FAILURES = """
CREATE TABLE login_failures (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT NOT NULL COLLATE NOCASE,
    failed_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT    NOT NULL,
            is_admin      INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT    NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id)")
    _ensure_login_failures()


def _ensure_login_failures() -> None:
    inspector = sa.inspect(op.get_bind())
    if "login_failures" not in inspector.get_table_names():
        op.execute(CREATE_LOGIN_FAILURES)
    elif "id" not in {column["name"] for column in inspector.get_columns("login_failures")}:
        # Rebuild the table with a primary key and copy every row across.
        op.execute("DROP INDEX IF EXISTS login_failures_user")
        op.execute("ALTER TABLE login_failures RENAME TO login_failures_legacy")
        op.execute(CREATE_LOGIN_FAILURES)
        op.execute(
            "INSERT INTO login_failures (username, failed_at) "
            "SELECT username, failed_at FROM login_failures_legacy"
        )
        op.execute("DROP TABLE login_failures_legacy")
    op.execute("CREATE INDEX IF NOT EXISTS login_failures_user ON login_failures(username)")


def downgrade() -> None:
    # Account data is never dropped by a downgrade.
    pass
