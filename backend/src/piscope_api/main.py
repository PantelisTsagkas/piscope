"""FastAPI application factory."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from piscope_api import __version__
from piscope_api.errors import register_error_handlers
from piscope_api.routers import analysis, dataset, experiments, search
from piscope_api.schemas.common import ErrorResponse
from piscope_api.settings import Settings
from piscope_api.state import build_state

API_PREFIX = "/api/v1"

DESCRIPTION = """
Explore, search and analyse the decimal digits of pi.

**Indexing.** Position 1 is the first digit after the decimal point (the `1` in
`3.14159...`). The integer digit `3` is not part of the dataset.

**Scientific scope.** Results describe a finite prefix of pi. The normality of pi has
not been proven, and passing statistical tests does not establish it.
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the API. Pass ``settings`` to override environment configuration."""
    resolved = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        app.state.piscope = build_state(resolved)
        yield
        if app.state.piscope.store is not None:
            app.state.piscope.store.close()

    app = FastAPI(
        title="PiScope API",
        version=__version__,
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
        openapi_url=f"{API_PREFIX}/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    api = APIRouter(
        prefix=API_PREFIX,
        responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    api.include_router(dataset.router)
    api.include_router(search.router)
    api.include_router(analysis.router)
    api.include_router(experiments.router)
    app.include_router(api)
    return app


def main() -> None:
    """Run the API with uvicorn (entry point for the ``piscope-api`` command)."""
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("piscope_api.main:create_app", factory=True, host="0.0.0.0", port=8000)
