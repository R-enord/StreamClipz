from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import auth
from ..config import Settings
from ..deps import current_user, get_db, get_settings
from ..templating import templates

router = APIRouter()


@router.get("/login")
def login_form(request: Request, user=Depends(current_user)):
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login_submit(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = auth.authenticate(db, settings, username, password)
    if user is None:
        if auth.is_locked(db, settings, username):
            message = f"Too many failed attempts. Wait {settings.login_lock_minutes} minutes and try again."
        else:
            message = "Wrong username or password."
        return templates.TemplateResponse(request, "login.html", {"error": message}, status_code=401)
    token = auth.create_session(db, settings, user)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return response


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    auth.delete_session(db, request.cookies.get(auth.SESSION_COOKIE))
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(auth.SESSION_COOKIE)
    return response
