"""Contrat d'erreur uniforme — RFC 7807 (application/problem+json).

Toutes les erreurs sortantes suivent la forme :
    { "type", "title", "status", "request_id", ... }

En production, aucune stack trace ni detail technique sensible n'est expose.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger(__name__)

_PROBLEM_MEDIA_TYPE = "application/problem+json"


class ProblemException(Exception):  # noqa: N818 - nom metier volontaire (Problem Details)
    """Erreur applicative portant un statut HTTP et un titre explicites."""

    def __init__(
        self,
        status: int,
        title: str,
        *,
        type_: str = "about:blank",
        detail: str | None = None,
    ) -> None:
        self.status = status
        self.title = title
        self.type_ = type_
        self.detail = detail
        super().__init__(title)


def _current_request_id() -> str | None:
    return structlog.contextvars.get_contextvars().get("request_id")


def _problem_response(
    *,
    status: int,
    title: str,
    type_: str = "about:blank",
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": type_,
        "title": title,
        "status": status,
        "request_id": _current_request_id(),
    }
    if extra:
        body.update(extra)
    return JSONResponse(status_code=status, content=body, media_type=_PROBLEM_MEDIA_TYPE)


def install_exception_handlers(app: FastAPI, *, is_production: bool) -> None:
    """Enregistre les gestionnaires d'exceptions sur l'application."""

    @app.exception_handler(ProblemException)
    async def _handle_problem(_: Request, exc: ProblemException) -> JSONResponse:
        extra = {"detail": exc.detail} if exc.detail else None
        return _problem_response(status=exc.status, title=exc.title, type_=exc.type_, extra=extra)

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        title = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
        return _problem_response(status=exc.status_code, title=title)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Les erreurs de validation portent sur l'entree client : on peut les
        # detailler sans risque de fuite d'information sensible.
        return _problem_response(
            status=HTTPStatus.UNPROCESSABLE_ENTITY,
            title="Validation Error",
            extra={"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Erreur non anticipee : journalisee en interne, generique cote client.
        logger.error("unhandled_exception", exc_info=exc)
        title = "Internal Server Error"
        extra = None if is_production else {"detail": f"{type(exc).__name__}: {exc}"}
        return _problem_response(status=HTTPStatus.INTERNAL_SERVER_ERROR, title=title, extra=extra)
