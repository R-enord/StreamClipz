"""Schema upgrades: a fresh database, and the database the first version of the app created."""

import sqlite3
from datetime import timedelta

import sqlalchemy as sa

from app.auth import authenticate, user_for_token
from app.config import Settings
from app.security import hash_password, hash_token
from core.clock import utcnow
from core.db import make_engine, make_session_factory, migrate

# A frozen copy of the schema the first version created by hand. Do not change it.
LEGACY_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    is_admin      INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
CREATE TABLE IF NOT EXISTS login_failures (
    username   TEXT NOT NULL COLLATE NOCASE,
    failed_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS login_failures_user ON login_failures(username);
"""


def table_names(path):
    engine = make_engine(path)
    try:
        return set(sa.inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_fresh_database_gets_every_table_and_can_be_migrated_twice(tmp_path):
    path = tmp_path / "fresh.db"
    migrate(path)
    migrate(path)
    assert {"users", "sessions", "login_failures", "jobs", "alembic_version"} <= table_names(path)


def test_legacy_database_is_upgraded_and_keeps_its_data(tmp_path):
    path = tmp_path / "legacy.db"
    raw = sqlite3.connect(path)
    raw.executescript(LEGACY_SCHEMA)
    raw.execute(
        "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
        ("owner", hash_password("legacy-password-1")),
    )
    raw.execute("INSERT INTO login_failures (username) VALUES ('owner')")
    token = "legacy-session-token"
    expires = (utcnow() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    raw.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, 1, ?)",
        (hash_token(token), expires),
    )
    raw.commit()
    raw.close()

    migrate(path)

    engine = make_engine(path)
    try:
        columns = {c["name"] for c in sa.inspect(engine).get_columns("login_failures")}
        assert "id" in columns
        with make_session_factory(engine)() as db:
            failures = db.execute(sa.text("SELECT COUNT(*) FROM login_failures")).scalar()
            assert failures == 1  # the legacy failure row survived the rebuild
            assert user_for_token(db, token).username == "owner"  # legacy session still works
            user = authenticate(db, Settings(data_dir=tmp_path), "owner", "legacy-password-1")
            assert user is not None and user.is_admin
    finally:
        engine.dispose()
