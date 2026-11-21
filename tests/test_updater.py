"""Updates replace the app's code, keep the data folder, and save what they replace."""

import zipfile
from pathlib import Path

import pytest

from core import updater


def make_release(path: Path, files: dict[str, str], top: str = "StreamClipz-main") -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(f"{top}/{name}", content)
    return path


def test_update_replaces_code_and_keeps_data_and_saves_the_old_files(tmp_path):
    release = make_release(tmp_path / "release.zip", {
        "app/main.py": "new code",
        "core/extra.py": "added",
        "requirements.txt": "",
        "update.bat": "NEW BAT",
        "data/streamclipz.db": "from the release",
        ".git/config": "git files",
    })
    app = tmp_path / "app"
    (app / "app").mkdir(parents=True)
    (app / "app" / "main.py").write_text("old code", encoding="utf-8")
    (app / "data").mkdir()
    (app / "data" / "streamclipz.db").write_text("your login", encoding="utf-8")
    (app / "update.bat").write_text("old bat", encoding="utf-8")
    backups = tmp_path / "backups"

    result = updater.apply_update(release, app, backups, install=False)

    assert (app / "app" / "main.py").read_text(encoding="utf-8") == "new code"
    assert (app / "core" / "extra.py").read_text(encoding="utf-8") == "added"
    assert (app / "data" / "streamclipz.db").read_text(encoding="utf-8") == "your login"
    assert (app / "update.bat").read_text(encoding="utf-8") == "old bat"
    assert not (app / ".git").exists()
    saved = list(backups.rglob("main.py"))
    assert len(saved) == 1 and saved[0].read_text(encoding="utf-8") == "old code"
    assert result["replaced"] == 1 and result["backup"] is not None  # only app/main.py existed before


def test_a_download_that_is_not_the_project_is_refused(tmp_path):
    bogus = make_release(tmp_path / "bogus.zip", {"readme.txt": "hello"})
    with pytest.raises(updater.UpdateError):
        updater.apply_update(bogus, tmp_path / "app", tmp_path / "backups", install=False)


def test_download_reads_from_an_address(tmp_path):
    source = tmp_path / "source.zip"
    source.write_bytes(b"PK-test-bytes")
    copy = updater.download(source.as_uri(), tmp_path / "copy.zip")
    assert copy.read_bytes() == b"PK-test-bytes"
