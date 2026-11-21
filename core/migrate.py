"""Upgrade the database to the latest schema.

    python -m core.migrate [--db PATH]

The app runs this automatically when it starts, so you only need it for manual checks.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .db import default_db_path, migrate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m core.migrate")
    parser.add_argument("--db", type=Path, default=None, help="Database file. Defaults to the data folder.")
    args = parser.parse_args(argv)
    db_path = args.db or default_db_path()
    migrate(db_path)
    print(f"Database is up to date: {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
