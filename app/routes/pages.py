from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from ..auth import User
from ..deps import current_user
from ..templating import templates

router = APIRouter()


@router.get("/")
def dashboard(request: Request, user: User | None = Depends(current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "dashboard.html", {"user": user})
