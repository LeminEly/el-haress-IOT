"""Connexion asynchrone a la base (SQLAlchemy 2.0 + asyncpg).

L'`account_id` de filtrage est applique en couche service a partir du contexte
d'authentification (module tenancy), jamais ici.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..config import get_settings


def create_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


engine: AsyncEngine = create_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependance FastAPI : fournit une session async par requete."""
    async with AsyncSessionLocal() as session:
        yield session
