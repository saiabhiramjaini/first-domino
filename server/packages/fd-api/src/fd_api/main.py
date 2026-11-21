"""Application factory: routers, error handlers, startup and shutdown."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fd_api.errors import install_error_handlers
from fd_api.routers import ROUTERS
from fd_api.services.diagnosis_runner import DiagnosisRunner
from fd_api.services.engine import EngineFactory, LlmEngineFactory
from fd_api.settings import ApiSettings
from fd_database.session import Database
from fd_shared.logging import configure_logging, get_logger

log = get_logger(__name__)

CONTRACT_VERSION = "3"


def _lifespan(settings: ApiSettings, database: Database | None, engine: EngineFactory | None):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db = database or Database()
        await db.create_tables()
        async with httpx.AsyncClient() as http:
            runner = DiagnosisRunner(db, engine or LlmEngineFactory(), http, settings)
            await runner.fail_interrupted()
            app.state.database = db
            app.state.diagnosis_runner = runner
            log.info("api.started")
            try:
                yield
            finally:
                await runner.shutdown()
                await db.dispose()

    return lifespan


def create_app(
    settings: ApiSettings | None = None,
    database: Database | None = None,
    engine: EngineFactory | None = None,
) -> FastAPI:
    """Builds the API app. Startup creates any missing tables.

    Args:
        settings: Settings to use. Read from the environment when omitted.
        database: Database to use. Built from `FD_DATABASE_*` settings when omitted.
        engine: The engine diagnoses run on. The real one, configured by `FD_ENGINE_*`, when
            omitted.
    """
    settings = settings or ApiSettings()
    configure_logging(settings.log_level, json_output=settings.log_json)
    app = FastAPI(
        lifespan=_lifespan(settings, database, engine),
        title="First Domino API",
        version=CONTRACT_VERSION,
        summary="Finds the step where a failed AI agent run became doomed, and proves it.",
        separate_input_output_schemas=False,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.state.settings = settings
    install_error_handlers(app)
    for router in ROUTERS:
        app.include_router(router)
    return app
