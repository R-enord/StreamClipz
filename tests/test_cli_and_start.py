import getpass
import importlib.util
import io
import sys
from pathlib import Path

from app import cli
from app.config import Settings
from app.db import connect

ROOT = Path(__file__).resolve().parent.parent


def test_create_user_defaults_to_computer_user_name(tmp_path, monkeypatch):
    monkeypatch.setenv("STREAMCLIPZ_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(getpass, "getuser", lambda: "Abdul")
    answers = iter(["correct-horse-battery", "correct-horse-battery"])
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": next(answers))

    assert cli.main(["create-user", "--admin"]) == 0

    conn = connect(Settings().db_path)
    row = conn.execute("SELECT username, is_admin FROM users").fetchone()
    conn.close()
    assert row["username"] == "Abdul" and row["is_admin"] == 1


def test_mismatched_passwords_create_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("STREAMCLIPZ_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(getpass, "getuser", lambda: "abdul")
    answers = iter(["correct-horse-battery", "something-else-entirely"])
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": next(answers))

    assert cli.main(["create-user"]) == 1
    conn = connect(Settings().db_path)
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    conn.close()


def test_start_without_account_and_no_terminal_stops_with_command(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("STREAMCLIPZ_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(getpass, "getuser", lambda: "abdul")
    spec = importlib.util.spec_from_file_location("start_script", ROOT / "scripts" / "start.py")
    start = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(start)
    monkeypatch.setattr(sys, "stdin", io.StringIO())  # not a terminal

    assert start.main([]) == 1
    out = capsys.readouterr().out
    assert "Your sign-in name will be: abdul" in out
    assert "create-user --admin" in out
