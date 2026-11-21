"""Sign-in, sessions and lockout. No HTTP here: the routes call these functions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from core.clock import utcnow
from core.models import LoginFailure, UserSession
from core.models import User as UserRecord

from .config import Settings
from .security import hash_password, hash_token, new_session_token, verify_password

SESSION_COOKIE = "sc_session"


@dataclass(frozen=True)
class User:
    id: int
    username: str
    is_admin: bool


def create_user(db: Session, username: str, password: str, *, is_admin: bool = False) -> int:
    username = username.strip()
    if not username or len(password) < 10:
        raise ValueError("Username is required and the password must be at least 10 characters.")
    record = UserRecord(username=username, password_hash=hash_password(password), is_admin=is_admin)
    db.add(record)
    db.commit()
    return record.id


def is_locked(db: Session, settings: Settings, username: str) -> bool:
    window_start = utcnow() - timedelta(minutes=settings.login_lock_minutes)
    failures = db.scalar(
        select(func.count())
        .select_from(LoginFailure)
        .where(LoginFailure.username == username, LoginFailure.failed_at >= window_start)
    )
    return (failures or 0) >= settings.max_login_failures


def authenticate(db: Session, settings: Settings, username: str, password: str) -> User | None:
    """Return the user for valid credentials, or None. Failures are counted per username."""
    if is_locked(db, settings, username):
        return None
    record = db.scalar(select(UserRecord).where(UserRecord.username == username.strip()))
    # Always run one hash check, so response timing does not reveal whether the user exists.
    stored = record.password_hash if record else hash_password("not-a-real-password!")
    password_matches = verify_password(password, stored)
    ok = record is not None and password_matches
    if ok:
        db.execute(
            delete(LoginFailure)
            .where(LoginFailure.username == username)
            .execution_options(synchronize_session=False)
        )
    else:
        db.add(LoginFailure(username=username, failed_at=utcnow()))
    db.commit()
    if not ok:
        return None
    return User(id=record.id, username=record.username, is_admin=bool(record.is_admin))


def create_session(db: Session, settings: Settings, user: User) -> str:
    token = new_session_token()
    db.add(
        UserSession(
            token_hash=hash_token(token),
            user_id=user.id,
            expires_at=utcnow() + timedelta(hours=settings.session_hours),
        )
    )
    db.commit()
    return token


def user_for_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    row = db.execute(
        select(UserRecord.id, UserRecord.username, UserRecord.is_admin, UserSession.expires_at)
        .join(UserSession, UserSession.user_id == UserRecord.id)
        .where(UserSession.token_hash == hash_token(token))
    ).first()
    if row is None or row.expires_at < utcnow():
        return None
    return User(id=row.id, username=row.username, is_admin=bool(row.is_admin))


def delete_session(db: Session, token: str | None) -> None:
    if not token:
        return
    db.execute(
        delete(UserSession)
        .where(UserSession.token_hash == hash_token(token))
        .execution_options(synchronize_session=False)
    )
    db.commit()


def purge_expired(db: Session) -> None:
    db.execute(
        delete(UserSession)
        .where(UserSession.expires_at < utcnow())
        .execution_options(synchronize_session=False)
    )
    db.commit()
