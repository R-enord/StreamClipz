"""Login, session lifecycle, and brute-force lockout. Routes call these; no HTTP here."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .config import Settings
from .db import transaction
from .security import hash_password, hash_token, new_session_token, verify_password

SESSION_COOKIE = "sc_session"


@dataclass(frozen=True)
class User:
    id: int
    username: str
    is_admin: bool


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def create_user(conn: sqlite3.Connection, username: str, password: str, *, is_admin: bool = False) -> int:
    username = username.strip()
    if not username or len(password) < 10:
        raise ValueError("Username is required and the password must be at least 10 characters.")
    with transaction(conn):
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
            (username, hash_password(password), int(is_admin)),
        )
    return int(cur.lastrowid)


def is_locked(conn: sqlite3.Connection, settings: Settings, username: str) -> bool:
    window_start = _fmt(_now() - timedelta(minutes=settings.login_lock_minutes))
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM login_failures WHERE username = ? AND failed_at >= ?",
        (username, window_start),
    ).fetchone()
    return row["n"] >= settings.max_login_failures


def authenticate(conn: sqlite3.Connection, settings: Settings, username: str, password: str) -> User | None:
    """Return the user for valid credentials, or None. Failures are counted per username."""
    if is_locked(conn, settings, username):
        return None
    row = conn.execute(
        "SELECT id, username, password_hash, is_admin FROM users WHERE username = ?",
        (username.strip(),),
    ).fetchone()
    # Always run one hash check so response timing does not reveal whether a user exists.
    stored = row["password_hash"] if row else hash_password("not-a-real-password!")
    ok = verify_password(password, stored) and row is not None
    with transaction(conn):
        if not ok:
            conn.execute("INSERT INTO login_failures (username) VALUES (?)", (username,))
        else:
            conn.execute("DELETE FROM login_failures WHERE username = ?", (username,))
    if not ok:
        return None
    return User(id=row["id"], username=row["username"], is_admin=bool(row["is_admin"]))


def create_session(conn: sqlite3.Connection, settings: Settings, user: User) -> str:
    token = new_session_token()
    expires = _now() + timedelta(hours=settings.session_hours)
    with transaction(conn):
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (hash_token(token), user.id, _fmt(expires)),
        )
    return token


def user_for_token(conn: sqlite3.Connection, token: str | None) -> User | None:
    if not token:
        return None
    row = conn.execute(
        """
        SELECT u.id, u.username, u.is_admin, s.expires_at
        FROM sessions s JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ?
        """,
        (hash_token(token),),
    ).fetchone()
    if row is None or row["expires_at"] < _fmt(_now()):
        return None
    return User(id=row["id"], username=row["username"], is_admin=bool(row["is_admin"]))


def delete_session(conn: sqlite3.Connection, token: str | None) -> None:
    if not token:
        return
    with transaction(conn):
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_token(token),))


def purge_expired(conn: sqlite3.Connection) -> None:
    with transaction(conn):
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (_fmt(_now()),))
