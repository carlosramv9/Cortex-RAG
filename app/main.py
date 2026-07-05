"""FastAPI application entrypoint.

Builds and configures the app: logging, lifespan (DB engine lifecycle),
middleware, CORS, error handlers, routers and OpenAPI metadata.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.v1.routers.api import api_router
from app.api.v1.routers.health import router as health_router
from app.config.settings import Settings, get_settings
from app.infrastructure.persistence.sqlalchemy.session import get_database
from app.shared.constants import API_V1_PREFIX
from app.shared.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup/shutdown resources (DB engine)."""
    settings: Settings = get_settings()
    app.state.settings = settings
    app.state.database = get_database(settings)
    logger.info("startup", env=settings.app.env.value, version=__version__)
    try:
        yield
    finally:
        await app.state.database.dispose()
        logger.info("shutdown")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    configure_logging(level=settings.app.log_level, json_logs=settings.app.log_json)

    app = FastAPI(
        title=settings.app.name,
        version=__version__,
        description="Decoupled RAG microservice for an AI-powered knowledge base.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    _configure_middleware(app, settings)
    register_exception_handlers(app)

    # Health lives at the root; feature endpoints are versioned under /api/v1.
    app.include_router(health_router)
    app.include_router(api_router, prefix=API_V1_PREFIX)

    return app


def _configure_middleware(app: FastAPI, settings: Settings) -> None:
    """Attach CORS and request-timing middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _timing_middleware(request: Request, call_next: object) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)  # type: ignore[operator]
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(elapsed_ms, 2),
        )
        return response


app = create_app()
