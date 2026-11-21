"""Database engine, sessions and migrations. SQLite now; PostgreSQL is a planned step."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

CORE_DIR = Path(__file__).resolve().parent
ROOT_DIR = CORE_DIR.parent


def default_db_path() -> Path:
    data_dir = Path(os.environ.get("STREAMCLIPZ_DATA_DIR", ROOT_DIR / "data"))
    return data_dir / "streamclipz.db"


def make_engine(db_path: Path) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        URL.create("sqlite", database=str(db_path)),
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def _configure_sqlite(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA busy_timeout = 30000")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def migrate(db_path: Path) -> None:
    """Bring the database up to the latest schema. Safe to run on every start."""
    config = Config(str(CORE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(CORE_DIR / "migrations"))
    config.attributes["db_path"] = db_path
    command.upgrade(config, "head")
