from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("STREAMCLIPZ_DATA_DIR", ROOT_DIR / "data"))
    )
    session_hours: int = field(
        default_factory=lambda: int(os.environ.get("STREAMCLIPZ_SESSION_HOURS", "720"))
    )
    cookie_secure: bool = field(
        default_factory=lambda: _env_bool("STREAMCLIPZ_COOKIE_SECURE", False)
    )
    # Failed logins allowed per username inside the window before a temporary lock.
    max_login_failures: int = 5
    login_lock_minutes: int = 15

    @property
    def db_path(self) -> Path:
        return self.data_dir / "streamclipz.db"

    @property
    def status_file(self) -> Path:
        """Where the SnipRiot worker writes its status (read-only for this app)."""
        return self.data_dir / "snipriot" / "status.json"
