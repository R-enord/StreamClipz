#!/usr/bin/env python3
"""Update Clipz Hub from GitHub. Your data is not changed. On Windows, double-click update.bat."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import updater  # noqa: E402


def main() -> int:
    print("Downloading the latest Clipz Hub code. This takes a few seconds...")
    try:
        with tempfile.TemporaryDirectory() as work:
            archive = updater.download(updater.DEFAULT_URL, Path(work) / "release.zip")
            result = updater.apply_update(archive, ROOT, Path.home() / "ClipzHub-backups")
    except (OSError, updater.UpdateError) as exc:
        print(f"The update did not finish: {exc}")
        print("Nothing in your data folder was changed. Check the internet connection and try again.")
        return 1
    print(f"Updated {result['copied']} files.")
    if result["backup"]:
        print(f"The replaced files were saved to {result['backup']}")
    print("Your data was not changed. Double-click start.bat to run Clipz Hub.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
