from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current time in UTC without tzinfo, which is how the database stores times."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
