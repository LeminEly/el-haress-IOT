"""Tests du moteur d'alertes, du dispatcher de notifications et des endpoints.

Moteur et endpoints utilisent la base reelle ; fakeredis pour le cooldown/gate et
des doublures pour les notifications (aucun envoi reel). Se saute si la base est
indisponible.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from fakeredis import aioredis as fake_aioredis
from fastapi.testclient import TestClient
from sqlalchemy import NullPool, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.alerting.alert_engine import AlertEngine, ReadingEvent
from src.alerting.alerting_models import (
    Alert,
    AlertCondition,
    AlertRule,
    AlertSeverity,
    AlertStatus,
)
from src.auth.auth_models import Account, AccountRole, AccountStatus
from src.auth.security import hash_password
from src.config import Settings, get_settings
from src.core.redis import get_blacklist_redis, get_ratelimit_redis
from src.db.session import get_session
from src.main import create_app
from src.notifications.notification_service import NotificationService
from src.notifications.providers import EmailProvider, TwilioProvider
from src.sensors.sensors_models import Gateway, Sensor

_TABLES = "accounts, gateways, sensors, readings, alert_rules, alerts, audit_log"
_PASSWORD = "motdepasse123"


def _engine():
    return create_async_engine(get_settings().database_url, poolclass=NullPool)


@pytest_asyncio.fixture
async def factory() -> AsyncIterator[async_sessionmaker]:
    engine = _engine()
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


class _FakeNotifier:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def dispatch(self, *, channels, phone, email, subject, body) -> None:
        self.calls.append({"channels": list(channels), "phone": phone, "email": email})


async def _seed(factory: async_sessionmaker, *, phone: str = "+22244000001") -> dict:
    async with factory() as session:
        account = Account(
            phone_number=phone,
            password_hash=hash_password(_PASSWORD, rounds=4),
            company_name="C",
            role=AccountRole.COMPANY,
            status=AccountStatus.ACTIVE,
            contact_email="ops@example.com",
        )
        session.add(account)
        await session.flush()
        gateway = Gateway(
            account_id=account.id,
            name="G",
            base_url="http://x",
            poll_interval_seconds=10,
            is_active=True,
        )
        session.add(gateway)
        await session.flush()
        sensor = Sensor(
            account_id=account.id,
            gateway_id=gateway.id,
            gateway_ref="16145",
            label="Temp",
            kind="temperature",
            unit="C",
            is_active=True,
        )
        session.add(sensor)
        await session.commit()
        return {"account": account.id, "sensor": sensor.id}


async def _add_rule(factory, ids, **overrides) -> uuid.UUID:
    defaults = {
        "account_id": ids["account"],
        "sensor_id": ids["sensor"],
        "name": "Temp critique",
        "condition": AlertCondition.GT,
        "threshold": 20.0,
        "duration_seconds": 0,
        "cooldown_minutes": 0,
        "severity": AlertSeverity.CRITICAL,
        "channels": ["email"],
        "is_active": True,
    }
    defaults.update(overrides)
    async with factory() as session:
        rule = AlertRule(**defaults)
        session.add(rule)
        await session.commit()
        return rule.id


async def _count_alerts(factory) -> int:
    async with factory() as session:
        return await session.scalar(select(func.count()).select_from(Alert))


# --- Moteur d'alertes -------------------------------------------------------


async def test_engine_triggers_and_notifies(factory: async_sessionmaker) -> None:
    ids = await _seed(factory)
    await _add_rule(factory, ids)
    notifier = _FakeNotifier()
    engine = AlertEngine(factory, fake_aioredis.FakeRedis(decode_responses=True), notifier)

    event = ReadingEvent(ids["account"], ids["sensor"], 25.0, datetime.now(UTC))
    triggered = await engine.evaluate(event)

    assert len(triggered) == 1
    assert await _count_alerts(factory) == 1
    assert notifier.calls == [
        {"channels": ["email"], "phone": "+22244000001", "email": "ops@example.com"}
    ]


async def test_engine_no_trigger_below_threshold(factory: async_sessionmaker) -> None:
    ids = await _seed(factory)
    await _add_rule(factory, ids)
    engine = AlertEngine(factory, fake_aioredis.FakeRedis(decode_responses=True))

    await engine.evaluate(ReadingEvent(ids["account"], ids["sensor"], 15.0, datetime.now(UTC)))
    assert await _count_alerts(factory) == 0


async def test_engine_cooldown_suppresses_repeat(factory: async_sessionmaker) -> None:
    ids = await _seed(factory)
    await _add_rule(factory, ids, cooldown_minutes=15)
    engine = AlertEngine(factory, fake_aioredis.FakeRedis(decode_responses=True))

    await engine.evaluate(ReadingEvent(ids["account"], ids["sensor"], 25.0, datetime.now(UTC)))
    await engine.evaluate(ReadingEvent(ids["account"], ids["sensor"], 26.0, datetime.now(UTC)))
    assert await _count_alerts(factory) == 1  # cooldown actif


async def test_engine_duration_gate(factory: async_sessionmaker) -> None:
    ids = await _seed(factory)
    rule_id = await _add_rule(factory, ids, duration_seconds=60)
    redis = fake_aioredis.FakeRedis(decode_responses=True)
    engine = AlertEngine(factory, redis)

    # Premier franchissement : gate non passe, pas d'alerte.
    await engine.evaluate(ReadingEvent(ids["account"], ids["sensor"], 25.0, datetime.now(UTC)))
    assert await _count_alerts(factory) == 0

    # Simule un franchissement soutenu depuis > 60 s.
    await redis.set(f"alert:breach:{rule_id}:{ids['sensor']}", time.time() - 120)
    await engine.evaluate(ReadingEvent(ids["account"], ids["sensor"], 25.0, datetime.now(UTC)))
    assert await _count_alerts(factory) == 1


async def test_engine_isolated_per_account(factory: async_sessionmaker) -> None:
    ids = await _seed(factory, phone="+22244000002")
    await _add_rule(factory, ids)
    engine = AlertEngine(factory, fake_aioredis.FakeRedis(decode_responses=True))

    # Un event d'une AUTRE entreprise n'active aucune regle de celle-ci.
    other_account = uuid.uuid4()
    await engine.evaluate(ReadingEvent(other_account, ids["sensor"], 25.0, datetime.now(UTC)))
    assert await _count_alerts(factory) == 0


# --- Dispatcher de notifications --------------------------------------------


class _Recorder:
    def __init__(self, channel: str) -> None:
        self.channel = channel
        self.sent: list[str] = []

    async def send(self, *, recipient: str, subject: str, body: str) -> None:
        self.sent.append(recipient)


class _Failing:
    channel = "sms"

    async def send(self, *, recipient: str, subject: str, body: str) -> None:
        raise RuntimeError("indisponible")


async def test_dispatch_routes_to_recipients() -> None:
    whatsapp = _Recorder("whatsapp")
    email = _Recorder("email")
    service = NotificationService({"whatsapp": whatsapp, "email": email})

    await service.dispatch(
        channels=["whatsapp", "email"],
        phone="+22244000003",
        email="ops@example.com",
        subject="s",
        body="b",
    )
    assert whatsapp.sent == ["+22244000003"]
    assert email.sent == ["ops@example.com"]


async def test_dispatch_skips_missing_recipient_and_survives_failure() -> None:
    service = NotificationService({"sms": _Failing(), "email": _Recorder("email")})
    # email destinataire absent -> ignore ; sms en echec -> ne bloque pas.
    await service.dispatch(
        channels=["email", "sms"], phone="+222", email=None, subject="s", body="b"
    )  # ne leve pas


async def test_providers_skip_when_unconfigured() -> None:
    settings = Settings(environment="testing")
    whatsapp = TwilioProvider(settings, channel="whatsapp", sender="", prefix="whatsapp:")
    email = EmailProvider(settings)
    assert whatsapp.configured is False
    assert email.configured is False
    # Non configures : ne tentent aucun envoi reseau et ne levent pas.
    await whatsapp.send(recipient="+22244000099", subject="s", body="b")
    await email.send(recipient="ops@example.com", subject="s", body="b")


# --- Endpoints alertes ------------------------------------------------------


@pytest.fixture
def client() -> Iterator[TestClient]:
    import asyncio

    engine = _engine()
    try:
        asyncio.run(_truncate(engine))
    except SQLAlchemyError:
        pytest.skip("base de donnees indisponible")

    app = create_app(Settings(environment="testing", cors_origins="http://localhost:5173"))

    async def _override_session():
        local = _engine()
        local_factory = async_sessionmaker(local, expire_on_commit=False)
        try:
            async with local_factory() as session:
                yield session
        finally:
            await local.dispose()

    fake = fake_aioredis.FakeRedis(decode_responses=True)
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_ratelimit_redis] = lambda: fake
    app.dependency_overrides[get_blacklist_redis] = lambda: fake

    with TestClient(app) as test_client:
        yield test_client


async def _truncate(engine) -> None:
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))
    finally:
        await engine.dispose()


async def _seed_alert(phone: str) -> dict:
    engine = _engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        ids = await _seed(factory, phone=phone)
        async with factory() as session:
            alert = Alert(
                account_id=ids["account"],
                sensor_id=ids["sensor"],
                severity=AlertSeverity.CRITICAL,
                value=25.0,
                status=AlertStatus.ACTIVE,
                triggered_at=datetime.now(UTC),
            )
            session.add(alert)
            await session.commit()
            ids["alert"] = alert.id
        return ids
    finally:
        await engine.dispose()


def _login(client: TestClient, phone: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"phone_number": phone, "password": _PASSWORD}
    )
    return response.json()["data"]["access_token"]


def test_alerts_listed_and_acknowledged_with_isolation(client: TestClient) -> None:
    import asyncio

    a = asyncio.run(_seed_alert("+22244000010"))
    b = asyncio.run(_seed_alert("+22244000011"))
    token_a = _login(client, "+22244000010")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    listing = client.get("/api/v1/alerts", headers=headers_a).json()["data"]
    assert len(listing) == 1
    assert listing[0]["id"] == str(a["alert"])

    # A ne peut pas acquitter l'alerte de B.
    assert client.post(f"/api/v1/alerts/{b['alert']}/ack", headers=headers_a).status_code == 404

    ack = client.post(f"/api/v1/alerts/{a['alert']}/ack", headers=headers_a)
    assert ack.status_code == 200
    assert ack.json()["data"]["status"] == "ACKNOWLEDGED"
