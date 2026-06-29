"""Configuration du logging structure (structlog).

JSON en production (machine-parseable), rendu console lisible en developpement.
Aucun `print` dans le code applicatif : on passe toujours par un logger.
"""

from __future__ import annotations

import logging

import structlog


def configure_logging(level: str = "INFO", *, json_logs: bool = True) -> None:
    """Configure structlog pour toute l'application.

    Args:
        level: niveau minimal (`DEBUG`, `INFO`, `WARNING`, ...).
        json_logs: sortie JSON si vrai (production), rendu console sinon.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Retourne un logger structure lie."""
    return structlog.get_logger(name)
