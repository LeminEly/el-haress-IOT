"""Bootstrap de l'application FastAPI El-Haress.

Assemble la configuration, le logging structure, les middleware transverses, le
contrat d'erreur RFC 7807 et les routes. Volontairement minimal en phase 0 :
l'application demarre a vide (endpoint de sante) sans dependance a la base ni a
Redis, conformement a la definition de termine de la phase Fondations.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .admin.admin_routes import router as admin_router
from .alerting.alerting_routes import alerts_router
from .alerting.alerting_routes import router as alerting_router
from .api.health_routes import router as health_router
from .api.ws_routes import router as ws_router
from .auth.accounts_routes import router as accounts_router
from .auth.auth_routes import router as auth_router
from .config import Settings, get_settings
from .core.exceptions import install_exception_handlers
from .core.logging import configure_logging, get_logger
from .core.middleware import install_request_context, install_security_headers
from .sensors.sensors_routes import router as sensors_router

_API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    configure_logging(settings.log_level, json_logs=settings.is_production)
    logger = get_logger(__name__)
    logger.info("backend_starting", environment=settings.environment)
    yield
    logger.info("backend_stopping")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construit et configure l'instance FastAPI."""
    settings = settings or get_settings()

    app = FastAPI(
        title="El-Haress API",
        version="0.1.0",
        docs_url=None if settings.is_production else f"{_API_PREFIX}/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else f"{_API_PREFIX}/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_request_context(app)
    install_security_headers(app, is_production=settings.is_production)
    install_exception_handlers(app, is_production=settings.is_production)

    app.include_router(health_router, prefix=_API_PREFIX)
    app.include_router(auth_router, prefix=_API_PREFIX)
    app.include_router(accounts_router, prefix=_API_PREFIX)
    app.include_router(admin_router, prefix=_API_PREFIX)
    app.include_router(sensors_router, prefix=_API_PREFIX)
    app.include_router(alerting_router, prefix=_API_PREFIX)
    app.include_router(alerts_router, prefix=_API_PREFIX)
    app.include_router(ws_router, prefix=_API_PREFIX)

    return app


app = create_app()
