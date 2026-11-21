"""Update the app from GitHub without touching your data.

Your data lives in its own folder (ClipzHub-data in your user folder), outside the app folder.
Replacing the app files therefore never changes it. Before a file is replaced, the old copy is
saved to ClipzHub-backups in your user folder.
"""

from __future__ import annotations

import datetime as dt
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_URL = "https://github.com/R-enord/StreamClipz/archive/refs/heads/claude/focused-brahmagupta-22ndjd.zip"
SKIP_DIRS = {".git", ".venv", "data", "__pycache__", ".pytest_cache", ".ruff_cache"}
SKIP_FILES = {"update.bat"}  # a .bat file that is running must not be overwritten while it runs


class UpdateError(Exception):
    """The update could not be applied."""


def download(url: str, destination: Path) -> Path:
    with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    return destination


def _skipped(relative: Path) -> bool:
    if relative.name in SKIP_FILES or relative.suffix == ".pyc":
        return True
    return any(part in SKIP_DIRS for part in relative.parts)


def install_requirements(app_dir: Path) -> None:
    command = [sys.executable, "-m", "pip", "install", "-q"]
    if sys.prefix == sys.base_prefix:  # not inside a virtual environment
        command.append("--user")
    command += ["-r", str(app_dir / "requirements.txt")]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise UpdateError("the app's parts could not be installed: " + result.stderr.strip()[-300:])


def apply_update(archive_path: Path, app_dir: Path, backup_root: Path, *, install: bool = True) -> dict:
    with tempfile.TemporaryDirectory() as work:
        extracted = Path(work)
        try:
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(extracted)
        except zipfile.BadZipFile as exc:
            raise UpdateError("the download was not a valid archive") from exc
        roots = [path for path in extracted.iterdir() if path.is_dir()]
        if len(roots) != 1 or not (roots[0] / "app" / "main.py").exists():
            raise UpdateError("the download does not look like Clipz Hub")
        release = roots[0]

        backup = backup_root / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        copied = replaced = 0
        for source in sorted(release.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(release)
            if _skipped(relative):
                continue
            target = app_dir / relative
            if target.exists():
                (backup / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup / relative)
                replaced += 1
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1
    if install:
        install_requirements(app_dir)
    return {"copied": copied, "replaced": replaced, "backup": str(backup) if replaced else None}
