from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .auth import purge_expired
from .config import Settings
from .db import connect, init_db
from .routes import api, auth_routes, pages

APP_DIR = Path(__file__).resolve().parent


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    init_db(settings.db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.conn = connect(settings.db_path)
        purge_expired(app.state.conn)
        yield
        app.state.conn.close()

    app = FastAPI(title="StreamClipz", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
    app.include_router(pages.router)
    app.include_router(auth_routes.router)
    app.include_router(api.router, prefix="/api")
    return app

