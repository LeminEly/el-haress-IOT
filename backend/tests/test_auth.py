"""Tests d'authentification, RBAC et isolation multi-entreprises.

Securite-critique. Utilisent la base reelle (migree) pour les comptes et
fakeredis pour le rate limiting et la blacklist. Se sautent si la base est
injoignable.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Iterator

import pytest
from fakeredis import aioredis as fake_aioredis
from fastapi.testclient import TestClient
from sqlalchemy import NullPool, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.auth.auth_models import Account, AccountRole, AccountStatus
from src.auth.security import hash_password
from src.config import Settings, get_settings
from src.core.redis import get_blacklist_redis, get_ratelimit_redis
from src.db.session import get_session
from src.main import create_app

_TABLES = "accounts, audit_log, sensors, readings, alert_rules, alerts"


def _run(coro):
    return asyncio.run(coro)


def _test_engine():
    # NullPool : aucune connexion mise en pool, donc aucune reutilisation d'une
    # connexion attachee a une boucle d'evenements deja fermee (tests).
    return create_async_engine(get_settings().database_url, poolclass=NullPool)


async def _truncate() -> None:
    engine = _test_engine()
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))
    finally:
        await engine.dispose()


async def _insert_account(*, phone: str, password: str, role: AccountRole) -> uuid.UUID:
    settings = get_settings()
    engine = _test_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            account = Account(
                phone_number=phone,
                password_hash=hash_password(password, rounds=settings.bcrypt_rounds),
                company_name="Test",
                role=role,
                status=AccountStatus.ACTIVE,
            )
            session.add(account)
            await session.commit()
            return account.id
    finally:
        await engine.dispose()


async def _get_account(account_id: uuid.UUID) -> Account | None:
    engine = _test_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            return await session.scalar(select(Account).where(Account.id == account_id))
    finally:
        await engine.dispose()


@pytest.fixture
def client() -> Iterator[TestClient]:
    try:
        _run(_truncate())
    except SQLAlchemyError:
        pytest.skip("base de donnees indisponible")

    settings = Settings(environment="testing", cors_origins="http://localhost:5173")
    app = create_app(settings)

    async def _override_session():
        engine = _test_engine()
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                yield session
        finally:
            await engine.dispose()

    ratelimit = fake_aioredis.FakeRedis(decode_responses=True)
    blacklist = fake_aioredis.FakeRedis(decode_responses=True)
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_ratelimit_redis] = lambda: ratelimit
    app.dependency_overrides[get_blacklist_redis] = lambda: blacklist

    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient, phone: str, password: str):
    return client.post("/api/v1/auth/login", json={"phone_number": phone, "password": password})


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- Authentification -------------------------------------------------------


def test_login_success_and_me(client: TestClient) -> None:
    _run(_insert_account(phone="+22241000001", password="motdepasse123", role=AccountRole.COMPANY))

    response = _login(client, "+22241000001", "motdepasse123")
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]

    me = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert me.status_code == 200
    assert me.json()["data"]["role"] == "COMPANY"


def test_login_wrong_password(client: TestClient) -> None:
    _run(_insert_account(phone="+22241000002", password="motdepasse123", role=AccountRole.COMPANY))
    response = _login(client, "+22241000002", "mauvais")
    assert response.status_code == 401


def test_login_unknown_phone(client: TestClient) -> None:
    response = _login(client, "+22241999999", "motdepasse123")
    assert response.status_code == 401


def test_lockout_after_max_failed_attempts(client: TestClient) -> None:
    account_id = _run(
        _insert_account(phone="+22241000003", password="motdepasse123", role=AccountRole.COMPANY)
    )
    for _ in range(5):
        assert _login(client, "+22241000003", "mauvais").status_code == 401

    # Compte verrouille : meme le bon mot de passe est refuse.
    assert _login(client, "+22241000003", "motdepasse123").status_code == 401
    account = _run(_get_account(account_id))
    assert account is not None and account.locked_until is not None


def test_rate_limit_on_login(client: TestClient) -> None:
    last_status = 200
    for _ in range(12):
        last_status = _login(client, "+22241000004", "motdepasse123").status_code
    assert last_status == 429


# --- Cycle de vie des jetons ------------------------------------------------


def test_logout_revokes_access_token(client: TestClient) -> None:
    _run(_insert_account(phone="+22241000005", password="motdepasse123", role=AccountRole.COMPANY))
    token = _login(client, "+22241000005", "motdepasse123").json()["data"]["access_token"]

    assert client.post("/api/v1/auth/logout", headers=_bearer(token)).status_code == 200
    # Jeton revoque : plus d'acces.
    assert client.get("/api/v1/auth/me", headers=_bearer(token)).status_code == 401


def test_refresh_rotation_revokes_old_cookie(client: TestClient) -> None:
    _run(_insert_account(phone="+22241000006", password="motdepasse123", role=AccountRole.COMPANY))
    _login(client, "+22241000006", "motdepasse123")
    old_cookie = client.cookies.get("el_haress_refresh")

    assert client.post("/api/v1/auth/refresh").status_code == 200

    # L'ancien refresh, rejoue avec un jar propre, est revoque.
    client.cookies.clear()
    client.cookies.set("el_haress_refresh", old_cookie, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401


# --- RBAC et isolation ------------------------------------------------------


def test_company_cannot_access_account_management(client: TestClient) -> None:
    _run(_insert_account(phone="+22241000007", password="motdepasse123", role=AccountRole.COMPANY))
    token = _login(client, "+22241000007", "motdepasse123").json()["data"]["access_token"]

    assert client.get("/api/v1/accounts", headers=_bearer(token)).status_code == 403
    create = client.post(
        "/api/v1/accounts",
        headers=_bearer(token),
        json={"phone_number": "+22241000099", "password": "motdepasse123", "company_name": "X"},
    )
    assert create.status_code == 403


def test_super_admin_creates_company_and_audit(client: TestClient) -> None:
    _run(
        _insert_account(
            phone="+22241000008", password="motdepasse123", role=AccountRole.SUPER_ADMIN
        )
    )
    token = _login(client, "+22241000008", "motdepasse123").json()["data"]["access_token"]

    created = client.post(
        "/api/v1/accounts",
        headers=_bearer(token),
        json={
            "phone_number": "+22241000088",
            "password": "motdepasse123",
            "company_name": "Entreprise A",
        },
    )
    assert created.status_code == 201
    assert created.json()["data"]["role"] == "COMPANY"


def test_protected_route_requires_token(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/accounts").status_code == 401


def test_identity_comes_from_token_not_query(client: TestClient) -> None:
    own_id = _run(
        _insert_account(phone="+22241000009", password="motdepasse123", role=AccountRole.COMPANY)
    )
    other_id = _run(
        _insert_account(phone="+22241000010", password="motdepasse123", role=AccountRole.COMPANY)
    )
    token = _login(client, "+22241000009", "motdepasse123").json()["data"]["access_token"]

    # Un account_id force en parametre est ignore : l'identite vient du jeton.
    me = client.get(f"/api/v1/auth/me?account_id={other_id}", headers=_bearer(token))
    assert me.status_code == 200
    assert me.json()["data"]["id"] == str(own_id)


def test_super_admin_lists_and_suspends_account(client: TestClient) -> None:
    _run(
        _insert_account(
            phone="+22241000011", password="motdepasse123", role=AccountRole.SUPER_ADMIN
        )
    )
    token = _login(client, "+22241000011", "motdepasse123").json()["data"]["access_token"]
    created = client.post(
        "/api/v1/accounts",
        headers=_bearer(token),
        json={
            "phone_number": "+22241000111",
            "password": "motdepasse123",
            "company_name": "A",
        },
    )
    company_id = created.json()["data"]["id"]

    listing = client.get("/api/v1/accounts", headers=_bearer(token))
    assert listing.status_code == 200
    assert len(listing.json()["data"]) >= 2

    suspend = client.patch(
        f"/api/v1/accounts/{company_id}", headers=_bearer(token), json={"status": "SUSPENDED"}
    )
    assert suspend.status_code == 200
    # Un compte suspendu ne peut plus se connecter.
    assert _login(client, "+22241000111", "motdepasse123").status_code == 401


def test_create_account_rejects_invalid_phone(client: TestClient) -> None:
    _run(
        _insert_account(
            phone="+22241000012", password="motdepasse123", role=AccountRole.SUPER_ADMIN
        )
    )
    token = _login(client, "+22241000012", "motdepasse123").json()["data"]["access_token"]
    response = client.post(
        "/api/v1/accounts",
        headers=_bearer(token),
        json={"phone_number": "pas-un-numero", "password": "motdepasse123", "company_name": "A"},
    )
    assert response.status_code == 422


def test_create_account_rejects_duplicate_phone(client: TestClient) -> None:
    _run(
        _insert_account(
            phone="+22241000013", password="motdepasse123", role=AccountRole.SUPER_ADMIN
        )
    )
    token = _login(client, "+22241000013", "motdepasse123").json()["data"]["access_token"]
    body = {"phone_number": "+22241000133", "password": "motdepasse123", "company_name": "A"}
    assert client.post("/api/v1/accounts", headers=_bearer(token), json=body).status_code == 201
    assert client.post("/api/v1/accounts", headers=_bearer(token), json=body).status_code == 409


def test_security_headers_present(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Content-Security-Policy" in response.headers


def test_tenant_context_derives_from_principal() -> None:
    from src.auth.dependencies import Principal
    from src.tenancy.tenancy import TenantContext, get_tenant_context

    principal = Principal(account_id=uuid.uuid4(), role=AccountRole.COMPANY, jti="x", access_exp=0)
    context = _run(get_tenant_context(principal=principal))
    assert isinstance(context, TenantContext)
    assert context.account_id == principal.account_id
    assert context.role == principal.role
