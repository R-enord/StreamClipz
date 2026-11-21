from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from .. import auth
from ..config import Settings
from ..deps import current_user, get_conn, get_settings
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
    conn=Depends(get_conn),
    settings: Settings = Depends(get_settings),
):
    user = auth.authenticate(conn, settings, username, password)
    if user is None:
        message = "Too many failed attempts. Wait 15 minutes and try again." if auth.is_locked(
            conn, settings, username
        ) else "Wrong username or password."
        return templates.TemplateResponse(
            request, "login.html", {"error": message}, status_code=401
        )
    token = auth.create_session(conn, settings, user)
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
def logout(request: Request, conn=Depends(get_conn)):
    auth.delete_session(conn, request.cookies.get(auth.SESSION_COOKIE))
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(auth.SESSION_COOKIE)
    return response
