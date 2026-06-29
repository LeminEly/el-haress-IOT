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


# En-tetes de securite appliques a chaque reponse. La CSP est restrictive : l'API
# ne sert pas de HTML ; le frontend (servi par Nginx) porte sa propre politique.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def install_security_headers(app: FastAPI, *, is_production: bool) -> None:
    """Ajoute les en-tetes de securite. HSTS uniquement en production (HTTPS)."""

    headers = dict(_SECURITY_HEADERS)
    if is_production:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    @app.middleware("http")
    async def _security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        for name, value in headers.items():
            response.headers.setdefault(name, value)
        return response
