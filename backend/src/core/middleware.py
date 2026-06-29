"""Middleware transverses.

`request_id` : chaque requete recoit un identifiant correle, present dans les
logs structures (via les contextvars structlog) et renvoye dans l'en-tete
`X-Request-ID`. Il alimente le champ `request_id` du contrat d'erreur RFC 7807.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response

_REQUEST_ID_HEADER = "X-Request-ID"


def install_request_context(app: FastAPI) -> None:
    """Installe le middleware de correlation de requete."""

    @app.middleware("http")
    async def _request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(_REQUEST_ID_HEADER) or str(uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers[_REQUEST_ID_HEADER] = request_id
        return response
