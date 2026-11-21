"""Alembic environment. It runs the migrations on the database path that core.db.migrate() passes in."""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import context

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.db import make_engine  # noqa: E402
from core.models import Base  # noqa: E402


def run_migrations_online() -> None:
    db_path = Path(context.config.attributes["db_path"])
    engine = make_engine(db_path)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=Base.metadata,
                render_as_batch=True,  # SQLite cannot alter most columns in place
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


run_migrations_online()
