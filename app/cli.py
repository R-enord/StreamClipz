"""Command line helpers. Run on the server, never over the network.

    python -m app.cli create-user <username> [--admin]

The password is typed at a hidden prompt and is never stored in plain text.
"""
from __future__ import annotations

import argparse
import getpass
import sys

from .auth import create_user
from .config import Settings
from .db import connect, init_db


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("create-user", help="Create a login account")
    add.add_argument("username")
    add.add_argument("--admin", action="store_true")
    args = parser.parse_args(argv)

    settings = Settings()
    init_db(settings.db_path)
    if args.command == "create-user":
        password = getpass.getpass("Password (min 10 characters): ")
        if password != getpass.getpass("Type it again: "):
            print("Passwords do not match.", file=sys.stderr)
            return 1
        conn = connect(settings.db_path)
        try:
            create_user(conn, args.username, password, is_admin=args.admin)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:  # duplicate username
            print(f"Could not create user: {exc}", file=sys.stderr)
            return 1
        finally:
            conn.close()
        print(f"Created user '{args.username}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
