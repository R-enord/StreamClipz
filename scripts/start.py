#!/usr/bin/env python3
"""Start StreamClipz and print the address to open on your phone.

Run this on the computer that hosts the app (your laptop):

    python scripts/start.py            (or double-click start.bat on Windows)

Stop it with Ctrl+C.
"""
from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from app.db import connect, init_db  # noqa: E402

TAILSCALE_WINDOWS_PATH = Path(r"C:\Program Files\Tailscale\tailscale.exe")


def lan_ip() -> str | None:
    """The address other devices on this Wi-Fi use to reach this computer.

    A UDP "connect" sends no packets. It only asks the OS which network interface it would use.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("192.0.2.1", 9))  # documentation-only address, never contacted
            return sock.getsockname()[0]
    except OSError:
        return None


def tailscale_ip() -> str | None:
    """Private address for reaching this computer from the phone away from home (free Tailscale app)."""
    exe = shutil.which("tailscale")
    if exe is None and TAILSCALE_WINDOWS_PATH.exists():
        exe = str(TAILSCALE_WINDOWS_PATH)
    if exe is None:
        return None
    try:
        result = subprocess.run([exe, "ip", "-4"], capture_output=True, text=True, timeout=5, check=True)
    except (subprocess.SubprocessError, OSError):
        return None
    addresses = result.stdout.split()
    return addresses[0] if addresses else None


def has_accounts(settings: Settings) -> bool:
    init_db(settings.db_path)
    conn = connect(settings.db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start StreamClipz for this computer and your phone.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    settings = Settings()
    if not has_accounts(settings):
        print("There is no login account yet. Create one first. You type the password yourself:")
        print("    python -m app.cli create-user yourname --admin")
        return 1

    port = args.port
    print()
    print("StreamClipz is starting.")
    print()
    print(f"  On this computer:          http://127.0.0.1:{port}")
    ip = lan_ip()
    if ip:
        print(f"  Phone, same Wi-Fi:         http://{ip}:{port}")
    else:
        print("  Phone, same Wi-Fi:         no Wi-Fi address found (check the connection)")
    ts = tailscale_ip()
    if ts:
        print(f"  Phone, anywhere (Tailscale): http://{ts}:{port}")
    print()
    print("If Windows asks about the firewall, allow access on Private networks.")
    print("Keep this window open. Stop with Ctrl+C.")
    print()
    sys.stdout.flush()

    command = [
        sys.executable, "-m", "uvicorn", "app.main:create_app", "--factory",
        "--host", "0.0.0.0", "--port", str(port),
    ]
    try:
        return subprocess.call(command, cwd=ROOT)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
