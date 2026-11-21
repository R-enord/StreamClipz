import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.db import connect  # noqa: E402
from app.main import create_app  # noqa: E402
from app.auth import create_user  # noqa: E402

PASSWORD = "correct-horse-battery"


@pytest.fixture()
def settings(tmp_path):
    return Settings(data_dir=tmp_path)


@pytest.fixture()
def client(settings):
    app = create_app(settings)
    conn = connect(settings.db_path)
    create_user(conn, "owner", PASSWORD, is_admin=True)
    conn.close()
    with TestClient(app) as c:
        yield c
