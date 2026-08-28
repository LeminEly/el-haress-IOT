"""Tests d'integration du schema TimescaleDB.

Necessitent une base migree (alembic upgrade head). Ils se sautent
automatiquement si la base est injoignable, pour ne pas bloquer un environnement
sans base.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from src.config import get_settings


@pytest_asyncio.fixture
async def db_conn() -> AsyncGenerator[AsyncConnection, None]:
    engine = create_async_engine(get_settings().database_url)
    try:
        conn = await engine.connect()
    except SQLAlchemyError:
        await engine.dispose()
        pytest.skip("base de donnees indisponible")
    try:
        yield conn
    finally:
        await conn.rollback()
        await conn.close()
        await engine.dispose()


async def test_readings_is_hypertable(db_conn: AsyncConnection) -> None:
    result = await db_conn.execute(
        text(
            "select count(*) from timescaledb_information.hypertables "
            "where hypertable_name = 'readings'"
        )
    )
    assert result.scalar_one() == 1


async def test_retention_policy_is_30_days(db_conn: AsyncConnection) -> None:
    result = await db_conn.execute(
        text(
            "select config->>'drop_after' from timescaledb_information.jobs "
            "where proc_name = 'policy_retention'"
        )
    )
    assert result.scalar_one() == "30 days"


async def test_compression_enabled(db_conn: AsyncConnection) -> None:
    result = await db_conn.execute(
        text(
            "select compression_enabled from timescaledb_information.hypertables "
            "where hypertable_name = 'readings'"
        )
    )
    assert result.scalar_one() is True


async def test_continuous_aggregates_exist(db_conn: AsyncConnection) -> None:
    result = await db_conn.execute(
        text(
            "select view_name from timescaledb_information.continuous_aggregates order by view_name"
        )
    )
    views = {row[0] for row in result}
    assert {"readings_1min", "readings_1hour"} <= views


async def test_audit_log_is_append_only(db_conn: AsyncConnection) -> None:
    await db_conn.execute(
        text(
            "insert into audit_log (id, action, created_at) "
            "values (gen_random_uuid(), 'test', now())"
        )
    )
    with pytest.raises(DBAPIError):
        await db_conn.execute(text("update audit_log set action = 'tampered'"))
