"""Application factory: routers, error handlers, startup and shutdown."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fd_api.errors import install_error_handlers
from fd_api.routers import ROUTERS
from fd_api.settings import ApiSettings
from fd_shared.logging import configure_logging

CONTRACT_VERSION = "1"


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    """Builds the API app.

    Args:
        settings: Settings to use. Read from the environment when omitted.
    """
    settings = settings or ApiSettings()
    configure_logging(settings.log_level, json_output=settings.log_json)
    app = FastAPI(
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
    install_error_handlers(app)
    for router in ROUTERS:
        app.include_router(router)
    return app
