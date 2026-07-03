"""Amorcage d'un environnement de demonstration.

Cree une passerelle STE2 et ses capteurs pour un compte existant.
Idempotent : peut etre execute plusieurs fois sans effet de bord.

Usage (depuis backend/, base accessible) :
    python scripts/seed_demo.py --phone +2224XXXXXX
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.auth.auth_models import Account
from src.auth.phone import normalize_phone
from src.config import get_settings
from src.sensors.sensors_models import Gateway, Sensor
from src.sensors.ste2_client import Ste2Client


async def _seed(phone: str, gateway_url: str) -> None:
    settings = get_settings()

    normalized = normalize_phone(phone, default_region=settings.default_phone_region)
    if normalized is None:
        raise SystemExit("Numero de telephone invalide")

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            account = await session.scalar(
                select(Account).where(Account.phone_number == normalized)
            )
            if account is None:
                raise SystemExit(f"Aucun compte trouve pour {normalized}")

            existing = await session.scalar(select(Gateway).where(Gateway.account_id == account.id))
            if existing is not None:
                print(f"Passerelle deja presente pour {account.company_name}")
                return

            gateway = Gateway(
                account_id=account.id,
                name="STE2 salle serveur",
                base_url=gateway_url,
                poll_interval_seconds=10,
                is_active=True,
            )
            session.add(gateway)
            await session.flush()

            client = Ste2Client()
            try:
                samples = await client.fetch_samples(gateway_url)
            except Exception as exc:
                raise SystemExit(
                    f"Impossible de contacter la passerelle {gateway_url} : {exc}"
                ) from exc

            existing_refs = set(
                await session.scalars(
                    select(Sensor.gateway_ref).where(Sensor.gateway_id == gateway.id)
                )
            )
            next_index = 1
            for sample in samples:
                if sample.gateway_ref in existing_refs:
                    continue
                sensor = Sensor(
                    account_id=account.id,
                    gateway_id=gateway.id,
                    gateway_ref=sample.gateway_ref,
                    hardware_id=sample.hardware_id,
                    label=sample.name or sample.gateway_ref,
                    kind=sample.kind,
                    unit=sample.unit,
                    device_index=next_index,
                    is_active=True,
                )
                session.add(sensor)
                next_index += 1

            await session.commit()
            print(
                f"Amorcage termine : {account.company_name} -> "
                f"{len(samples)} capteur(s) sur {gateway_url}"
            )

    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Amorce un environnement de demonstration")
    parser.add_argument("--phone", required=True, help="numero du compte existant")
    parser.add_argument(
        "--gateway-url",
        default="http://192.168.1.105",
        help="URL de la passerelle STE2 (defaut: http://192.168.1.105)",
    )
    args = parser.parse_args()

    asyncio.run(_seed(args.phone, args.gateway_url))


if __name__ == "__main__":
    main()
