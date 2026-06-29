"""Tests de l'API REST, du WebSocket et de l'isolation cross-tenant.

Deux entreprises A et B sont semees avec leurs propres donnees ; on verifie qu'un
jeton ne voit jamais les donnees de l'autre, sur chaque endpoint. Base reelle,
fakeredis pour redis. Se saute si la base est indisponible.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fakeredis import aioredis as fake_aioredis
from fastapi.testclient import TestClient
from sqlalchemy import NullPool, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.auth.auth_models import Account, AccountRole, AccountStatus
from src.auth.security import hash_password
from src.config import Settings, get_settings
from src.core.live import channel_for, publish_reading
from src.core.redis import get_blacklist_redis, get_pubsub_redis, get_ratelimit_redis
from src.db.session import get_session
from src.main import create_app
from src.sensors.sensors_models import Gateway, Reading, Sensor

_TABLES = "accounts, gateways, sensors, readings, alert_rules, alerts, audit_log"
_PASSWORD = "motdepasse123"


def _run(coro):
    return asyncio.run(coro)


def _engine():
    return create_async_engine(get_settings().database_url, poolclass=NullPool)


async def _truncate() -> None:
    engine = _engine()
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))
    finally:
        await engine.dispose()


async def _seed_company(phone: str, gateway_ref: str) -> dict[str, uuid.UUID]:
    engine = _engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            account = Account(
                phone_number=phone,
                password_hash=hash_password(_PASSWORD, rounds=get_settings().bcrypt_rounds),
                company_name="C",
                role=AccountRole.COMPANY,
                status=AccountStatus.ACTIVE,
            )
            session.add(account)
            await session.flush()
            gateway = Gateway(
                account_id=account.id,
                name="G",
                base_url="http://192.0.2.10",
                poll_interval_seconds=10,
                is_active=True,
            )
            session.add(gateway)
            await session.flush()
            sensor = Sensor(
                account_id=account.id,
                gateway_id=gateway.id,
                gateway_ref=gateway_ref,
                label="Temp",
                kind="temperature",
                unit="C",
                is_active=True,
            )
            session.add(sensor)
            await session.flush()
            session.add(
                Reading(
                    account_id=account.id,
                    sensor_id=sensor.id,
                    recorded_at=datetime.now(UTC),
                    value=25.0,
                )
            )
            await session.commit()
            ids = {"account": account.id, "gateway": gateway.id, "sensor": sensor.id}
    finally:
        await engine.dispose()
    return ids


@pytest.fixture
def client() -> Iterator[TestClient]:
    try:
        _run(_truncate())
    except SQLAlchemyError:
        pytest.skip("base de donnees indisponible")

    app = create_app(Settings(environment="testing", cors_origins="http://localhost:5173"))

    async def _override_session():
        engine = _engine()
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                yield session
        finally:
            await engine.dispose()

    fake = fake_aioredis.FakeRedis(decode_responses=True)
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_ratelimit_redis] = lambda: fake
    app.dependency_overrides[get_blacklist_redis] = lambda: fake
    app.dependency_overrides[get_pubsub_redis] = lambda: fake

    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient, phone: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"phone_number": phone, "password": _PASSWORD}
    )
    return response.json()["data"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- Isolation cross-tenant sur les donnees ---------------------------------


def test_sensors_isolated_per_company(client: TestClient) -> None:
    a = _seed_via(client, "+22243000001", "16145")
    b = _seed_via(client, "+22243000002", "12571")
    token_a = _login(client, "+22243000001")

    sensors = client.get("/api/v1/sensors", headers=_auth(token_a)).json()["data"]
    ids = {s["id"] for s in sensors}
    assert str(a["sensor"]) in ids
    assert str(b["sensor"]) not in ids


def test_readings_isolated_and_param_ignored(client: TestClient) -> None:
    _seed_via(client, "+22243000003", "16145")
    b = _seed_via(client, "+22243000004", "12571")
    token_a = _login(client, "+22243000003")

    own = client.get("/api/v1/readings", headers=_auth(token_a)).json()["data"]
    assert len(own) == 1

    # Forcer le sensor_id d'une AUTRE entreprise ne fuite rien (filtre account_id).
    forced = client.get(f"/api/v1/readings?sensor_id={b['sensor']}", headers=_auth(token_a)).json()[
        "data"
    ]
    assert forced == []


def test_update_other_company_sensor_returns_404(client: TestClient) -> None:
    _seed_via(client, "+22243000005", "16145")
    b = _seed_via(client, "+22243000006", "12571")
    token_a = _login(client, "+22243000005")

    response = client.patch(
        f"/api/v1/sensors/{b['sensor']}", headers=_auth(token_a), json={"label": "pirate"}
    )
    assert response.status_code == 404


def test_latest_and_dashboard_scoped(client: TestClient) -> None:
    a = _seed_via(client, "+22243000007", "16145")
    _seed_via(client, "+22243000008", "12571")
    token_a = _login(client, "+22243000007")

    latest = client.get("/api/v1/readings/latest", headers=_auth(token_a)).json()["data"]
    assert len(latest) == 1
    assert latest[0]["sensor_id"] == str(a["sensor"])

    summary = client.get("/api/v1/dashboard/summary", headers=_auth(token_a)).json()["data"]
    assert summary["sensors_total"] == 1


# --- Passerelles et regles d'alerte -----------------------------------------


def test_gateway_create_and_list(client: TestClient) -> None:
    _seed_via(client, "+22243000009", "16145")
    token = _login(client, "+22243000009")

    created = client.post(
        "/api/v1/gateways",
        headers=_auth(token),
        json={"name": "Salle B", "base_url": "http://192.0.2.20"},
    )
    assert created.status_code == 201
    listing = client.get("/api/v1/gateways", headers=_auth(token)).json()["data"]
    assert len(listing) == 2  # celle semee + la nouvelle


def test_alert_rule_crud_and_cross_tenant(client: TestClient) -> None:
    a = _seed_via(client, "+22243000010", "16145")
    b = _seed_via(client, "+22243000011", "12571")
    token_a = _login(client, "+22243000010")

    # Regle ciblant le capteur d'une autre entreprise -> refusee.
    bad = client.post(
        "/api/v1/alert-rules",
        headers=_auth(token_a),
        json={
            "name": "x",
            "sensor_id": str(b["sensor"]),
            "condition": "GT",
            "threshold": 20.0,
            "severity": "CRITICAL",
            "channels": ["email"],
        },
    )
    assert bad.status_code == 422

    created = client.post(
        "/api/v1/alert-rules",
        headers=_auth(token_a),
        json={
            "name": "Temp critique",
            "sensor_id": str(a["sensor"]),
            "condition": "GT",
            "threshold": 20.0,
            "severity": "CRITICAL",
            "channels": ["whatsapp", "sms", "email"],
        },
    )
    assert created.status_code == 201
    rule_id = created.json()["data"]["id"]

    assert len(client.get("/api/v1/alert-rules", headers=_auth(token_a)).json()["data"]) == 1

    # A modifie sa propre regle (succes, dont channels).
    updated = client.patch(
        f"/api/v1/alert-rules/{rule_id}",
        headers=_auth(token_a),
        json={"threshold": 22.0, "channels": ["email"]},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["threshold"] == 22.0

    token_b = _login(client, "+22243000011")
    # B ne peut pas modifier la regle de A.
    assert (
        client.patch(
            f"/api/v1/alert-rules/{rule_id}", headers=_auth(token_b), json={"threshold": 99.0}
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/v1/alert-rules/{rule_id}", headers=_auth(token_a)).status_code == 204
    )


def test_update_own_sensor(client: TestClient) -> None:
    a = _seed_via(client, "+22243000012", "16145")
    token = _login(client, "+22243000012")

    response = client.patch(
        f"/api/v1/sensors/{a['sensor']}",
        headers=_auth(token),
        json={"label": "Temperature salle A", "kind": "temperature", "is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["data"]["label"] == "Temperature salle A"
    assert response.json()["data"]["is_active"] is False


def test_readings_aggregated_bucket(client: TestClient) -> None:
    _seed_via(client, "+22243000013", "16145")
    token = _login(client, "+22243000013")

    # Agregat continu interroge correctement (vide tant qu'il n'est pas materialise).
    response = client.get("/api/v1/readings?bucket=1min", headers=_auth(token))
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


def test_endpoints_require_token(client: TestClient) -> None:
    for path in ("/api/v1/sensors", "/api/v1/readings", "/api/v1/alert-rules"):
        assert client.get(path).status_code == 401


# --- Temps reel : auth WebSocket et isolation pub/sub -----------------------


def test_ws_rejects_without_token(client: TestClient) -> None:
    # Parametre `token` requis : le handshake est refuse.
    with pytest.raises(Exception), client.websocket_connect("/api/v1/ws/live"):  # noqa: B017
        pass


def test_ws_rejects_invalid_token(client: TestClient) -> None:
    # Jeton invalide : la connexion est fermee avant acceptation.
    with (
        pytest.raises(Exception),  # noqa: B017
        client.websocket_connect("/api/v1/ws/live?token=invalide"),
    ):
        pass


async def test_pubsub_isolated_per_account() -> None:
    redis = fake_aioredis.FakeRedis(decode_responses=True)
    account_a = uuid.uuid4()
    account_b = uuid.uuid4()

    sub_a = redis.pubsub()
    await sub_a.subscribe(channel_for(account_a))
    await sub_a.get_message(timeout=1)  # consomme la confirmation d'abonnement
    sub_b = redis.pubsub()
    await sub_b.subscribe(channel_for(account_b))
    await sub_b.get_message(timeout=1)

    await publish_reading(redis, account_id=account_a, payload={"sensor_id": "s", "value": 30.5})
    await asyncio.sleep(0.05)

    message_a = await sub_a.get_message(ignore_subscribe_messages=True, timeout=1)
    assert message_a is not None and "sensor_id" in message_a["data"]

    message_b = await sub_b.get_message(ignore_subscribe_messages=True, timeout=1)
    assert message_b is None


def _seed_via(client: TestClient, phone: str, gateway_ref: str) -> dict[str, uuid.UUID]:
    return _run(_seed_company(phone, gateway_ref))
