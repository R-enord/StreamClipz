from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.db import make_engine, make_session_factory, migrate

from . import auth
from .config import Settings
from .routes import api, auth_routes, pages

APP_DIR = Path(__file__).resolve().parent


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    migrate(settings.db_path)  # upgrades the database schema before anything reads it
    engine = make_engine(settings.db_path)
    session_factory = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        with session_factory() as db:
            auth.purge_expired(db)
        yield
        engine.dispose()

    app = FastAPI(title="StreamClipz", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
    app.include_router(pages.router)
    app.include_router(auth_routes.router)
    app.include_router(api.router, prefix="/api")
    return app
