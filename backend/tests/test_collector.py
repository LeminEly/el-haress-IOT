"""Tests du parsing STE2 et du cycle de collecte.

Le parsing est teste sur le XML reel capture sur la passerelle (sans reseau). Le
cycle de collecte utilise un faux client (aucun acces a l'appareil) et la base
reelle (se saute si indisponible).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import NullPool, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.auth.auth_models import Account, AccountRole, AccountStatus
from src.collector.collector_service import CollectorService
from src.config import get_settings
from src.sensors.sensors_models import Gateway, Reading, Sensor
from src.sensors.ste2_parser import (
    Ste2Sample,
    infer_kind,
    merge_identities,
    parse_identities,
    parse_values,
)

# --- XML reel releve sur la passerelle STE2 LITE ---------------------------

VALUES_XML = """<?xml version="1.0" encoding="utf-8"?>
<val:Root xmlns:val="http://www.hw-group.com/XMLSchema/ste/values.xsd">
<SenSet>
  <Entry><ID>6686</ID><Name>Sensor 6686</Name><Units></Units>
    <Value>-999.9</Value><State>0</State></Entry>
  <Entry><ID>12571</ID><Name>Flood</Name><Units></Units>
    <Value>-999.9</Value><Resistance>0</Resistance><State>0</State></Entry>
  <Entry><ID>16145</ID><Name>Sensor 16145</Name><Units>C</Units>
    <Value>30.5</Value><State>1</State></Entry>
</SenSet>
</val:Root>
"""

CONFIG_XML = """<?xml version="1.0" ?>
<set:Root xmlns:set="http://www.etech.cz/XMLSchema/poseidon/values.xsd">
<sensor id="16145"><SenId>28113fe50e0000a5</SenId><SenName>Sensor 16145</SenName></sensor>
<sensor id="6686"><SenId>281e1a6704c80aa3</SenId><SenName>Sensor 6686</SenName></sensor>
</set:Root>
"""

_TABLES = "accounts, gateways, sensors, readings, alert_rules, alerts, audit_log"


# --- Parsing (pur, sans reseau) ---------------------------------------------


def test_parse_values_marks_invalid_samples() -> None:
    samples = {s.gateway_ref: s for s in parse_values(VALUES_XML)}
    assert set(samples) == {"6686", "12571", "16145"}

    live = samples["16145"]
    assert live.valid is True
    assert live.value == 30.5
    assert live.unit == "C"

    assert samples["6686"].valid is False  # -999.9 / State 0
    assert samples["6686"].value is None
    assert samples["12571"].valid is False  # detecteur non connecte


def test_parse_identities_and_merge() -> None:
    identities = parse_identities(CONFIG_XML)
    assert identities["16145"] == "28113fe50e0000a5"

    merged = {s.gateway_ref: s for s in merge_identities(parse_values(VALUES_XML), identities)}
    assert merged["16145"].hardware_id == "28113fe50e0000a5"


def test_infer_kind() -> None:
    assert infer_kind("C") == "temperature"
    assert infer_kind("%") == "humidity"
    assert infer_kind(None) == "unknown"
    assert infer_kind("") == "unknown"


# --- Cycle de collecte (faux client, base reelle) ---------------------------


class _FakeClient:
    def __init__(self, samples: list[Ste2Sample]) -> None:
        self._samples = samples

    async def fetch_samples(self, base_url: str) -> list[Ste2Sample]:
        return list(self._samples)


class _FailingClient:
    async def fetch_samples(self, base_url: str) -> list[Ste2Sample]:
        raise httpx.ConnectError("passerelle injoignable")


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker]:
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))
    except SQLAlchemyError:
        await engine.dispose()
        pytest.skip("base de donnees indisponible")
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def _seed_gateway(factory: async_sessionmaker) -> tuple[uuid.UUID, uuid.UUID]:
    async with factory() as session:
        account = Account(
            phone_number="+22242000001",
            password_hash="x",
            company_name="Entreprise",
            role=AccountRole.COMPANY,
            status=AccountStatus.ACTIVE,
        )
        session.add(account)
        await session.flush()
        gateway = Gateway(
            account_id=account.id,
            name="STE2 salle A",
            base_url="http://192.0.2.10",
            poll_interval_seconds=10,
            is_active=True,
        )
        session.add(gateway)
        await session.commit()
        return account.id, gateway.id


_SAMPLES = [
    Ste2Sample(
        gateway_ref="16145",
        name="Sensor 16145",
        unit="C",
        kind="temperature",
        value=30.5,
        valid=True,
        hardware_id="28113fe50e0000a5",
    ),
    Ste2Sample(
        gateway_ref="6686", name="Sensor 6686", unit=None, kind="unknown", value=None, valid=False
    ),
]


async def test_cycle_provisions_sensors_and_inserts_readings(
    session_factory: async_sessionmaker,
) -> None:
    account_id, gateway_id = await _seed_gateway(session_factory)

    results = await CollectorService(session_factory, _FakeClient(_SAMPLES)).run_cycle()

    assert len(results) == 1
    result = results[0]
    assert result.sensors_seen == 2
    assert result.readings_inserted == 1  # seul 16145 est valide
    assert result.mute == 1

    async with session_factory() as session:
        sensors = {s.gateway_ref: s for s in await session.scalars(select(Sensor))}
        assert set(sensors) == {"16145", "6686"}
        assert sensors["16145"].kind == "temperature"
        assert sensors["16145"].hardware_id == "28113fe50e0000a5"
        assert sensors["16145"].last_seen_at is not None

        # Isolation : la mesure porte l'account_id de la passerelle.
        readings = list(await session.scalars(select(Reading)))
        assert len(readings) == 1
        assert readings[0].account_id == account_id
        assert readings[0].value == 30.5

        gateway = await session.get(Gateway, gateway_id)
        assert gateway is not None and gateway.last_polled_at is not None


async def test_binary_sensor_triggered_state_stays_visible(
    session_factory: async_sessionmaker,
) -> None:
    # Un detecteur binaire (flood) ne doit jamais disparaitre. A l'etat normal il
    # lit une valeur (0) ; a l'etat declenche l'appareil sort la valeur de la plage
    # (sentinelle -999.9, status_state=2). On enregistre alors l'etat 1 (Detecte),
    # au lieu de le traiter comme muet et de le masquer.
    await _seed_gateway(session_factory)
    normal = _FakeClient(
        [
            Ste2Sample(
                gateway_ref="12571",
                name="Flood",
                unit="WLD",
                kind="flood",
                value=0.0,
                valid=True,
                status_state="1",
            )
        ]
    )
    await CollectorService(session_factory, normal).run_cycle()

    triggered = _FakeClient(
        [
            Ste2Sample(
                gateway_ref="12571",
                name="Flood",
                unit=None,
                kind="unknown",
                value=None,
                valid=False,
                status_state="2",
            )
        ]
    )
    result = (await CollectorService(session_factory, triggered).run_cycle())[0]

    assert result.readings_inserted == 1  # enregistre malgre la sentinelle
    assert result.mute == 0

    async with session_factory() as session:
        flood = (await session.scalars(select(Sensor).where(Sensor.gateway_ref == "12571"))).one()
        assert flood.kind == "flood"
        assert flood.last_seen_at is not None  # reste en ligne
        readings = list(await session.scalars(select(Reading)))
        assert len(readings) == 2
        assert max(readings, key=lambda r: r.recorded_at).value == 1.0  # Detecte


async def test_cycle_reuses_existing_sensor(session_factory: async_sessionmaker) -> None:
    _, gateway_id = await _seed_gateway(session_factory)
    async with session_factory() as session:
        gateway = await session.get(Gateway, gateway_id)
        assert gateway is not None
        session.add(
            Sensor(
                account_id=gateway.account_id,
                gateway_id=gateway.id,
                gateway_ref="16145",
                label="Pre-declare",
                kind="temperature",
                unit="C",
                is_active=True,
            )
        )
        await session.commit()

    await CollectorService(session_factory, _FakeClient(_SAMPLES)).run_cycle()

    async with session_factory() as session:
        count = await session.scalar(
            select(func.count()).select_from(Sensor).where(Sensor.gateway_ref == "16145")
        )
        assert count == 1  # reutilise, pas de doublon


async def test_cycle_resilient_to_gateway_failure(
    session_factory: async_sessionmaker,
) -> None:
    await _seed_gateway(session_factory)

    results = await CollectorService(session_factory, _FailingClient()).run_cycle()

    assert len(results) == 1
    assert results[0].error is not None
    assert results[0].readings_inserted == 0
    async with session_factory() as session:
        assert (await session.scalar(select(func.count()).select_from(Reading))) == 0
