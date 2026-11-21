from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from . import auth
from .auth import SESSION_COOKIE, User
from .config import Settings


def get_db(request: Request) -> Iterator[Session]:
    """One database session per request, closed when the request ends."""
    with request.app.state.session_factory() as db:
        yield db


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    return auth.user_for_token(db, request.cookies.get(SESSION_COOKIE))


def require_user(user: Annotated[User | None, Depends(current_user)]) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in")
    return user
