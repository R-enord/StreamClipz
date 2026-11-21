"""Command line helpers. Run on the server, never over the network.

    python -m app.cli create-user [username] [--admin]

The username defaults to your computer's user name. The password is typed at a hidden
prompt and is never stored in plain text.
"""
from __future__ import annotations

import argparse
import getpass
import sys

from .auth import create_user
from .config import Settings
from .db import connect, init_db

FALLBACK_USERNAME = "owner"


def default_username() -> str:
    """Your computer's user name (on Windows, the folder name under C:\\Users)."""
    try:
        name = getpass.getuser().strip()
    except Exception:  # no user name available in this environment
        name = ""
    return name or FALLBACK_USERNAME


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("create-user", help="Create a login account")
    add.add_argument("username", nargs="?", help="Defaults to your computer's user name")
    add.add_argument("--admin", action="store_true")
    args = parser.parse_args(argv)

    settings = Settings()
    init_db(settings.db_path)
    username = (args.username or default_username()).strip()
    password = getpass.getpass(f"Password for '{username}' (at least 10 characters, nothing shows while you type): ")
    if password != getpass.getpass("Type it again: "):
        print("Passwords do not match.", file=sys.stderr)
        return 1
    conn = connect(settings.db_path)
    try:
        create_user(conn, username, password, is_admin=args.admin)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # e.g. the username already exists
        print(f"Could not create '{username}': {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    print(f"Created login '{username}'. Sign in with that name and your password.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
