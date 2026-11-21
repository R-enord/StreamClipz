import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.auth import create_user  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from core.db import make_engine, make_session_factory  # noqa: E402

PASSWORD = "correct-horse-battery"


@pytest.fixture()
def settings(tmp_path):
    return Settings(data_dir=tmp_path)


@pytest.fixture()
def client(settings):
    app = create_app(settings)  # migrates the database
    engine = make_engine(settings.db_path)
    with make_session_factory(engine)() as db:
        create_user(db, "owner", PASSWORD, is_admin=True)
    engine.dispose()
    with TestClient(app) as c:
        yield c
