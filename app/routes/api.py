from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..auth import User
from ..config import Settings
from ..deps import get_settings, require_user

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Public: lets the phone (or a tunnel monitor) check the server is up."""
    return {"status": "ok"}


@router.get("/me")
def me(user: User = Depends(require_user)) -> dict[str, Any]:
    return {"username": user.username, "is_admin": user.is_admin}


@router.get("/status")
def snipriot_status(
    user: User = Depends(require_user), settings: Settings = Depends(get_settings)
) -> JSONResponse:
    """Read-only view of SnipRiot's status file, once the worker's data folder is present."""
    path = settings.status_file
    if not path.exists():
        return JSONResponse({"available": False, "detail": f"No status file at {path}"})
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return JSONResponse({"available": False, "detail": f"Status file unreadable: {exc}"})
    return JSONResponse({"available": True, "status": payload})
