from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from .auth import SESSION_COOKIE, User, user_for_token


def get_conn(request: Request):
    return request.app.state.conn


def get_settings(request: Request):
    return request.app.state.settings


def current_user(request: Request) -> User | None:
    return user_for_token(request.app.state.conn, request.cookies.get(SESSION_COOKIE))


def require_user(user: Annotated[User | None, Depends(current_user)]) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in")
    return user
