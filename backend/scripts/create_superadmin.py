"""Amorcage : creation du premier compte SUPER_ADMIN.

Il n'existe aucune auto-inscription ; ce script sert a creer l'operateur initial
de la plateforme. Le mot de passe est saisi de maniere interactive, jamais passe
en argument (pas de trace dans l'historique shell).

Usage (depuis backend/, base accessible) :
    python scripts/create_superadmin.py --phone +2224XXXXXX --company "Operateur"
"""

from __future__ import annotations

import argparse
import asyncio
import getpass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.auth.auth_models import Account, AccountRole, AccountStatus
from src.auth.phone import normalize_phone
from src.auth.security import hash_password
from src.config import get_settings


async def _create(phone: str, company: str, password: str) -> None:
    settings = get_settings()
    normalized = normalize_phone(phone, default_region=settings.default_phone_region)
    if normalized is None:
        raise SystemExit("Numero de telephone invalide")

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            existing = await session.scalar(
                select(Account).where(Account.phone_number == normalized)
            )
            if existing is not None:
                raise SystemExit("Un compte existe deja pour ce numero")
            session.add(
                Account(
                    phone_number=normalized,
                    password_hash=hash_password(password, rounds=settings.bcrypt_rounds),
                    company_name=company,
                    role=AccountRole.SUPER_ADMIN,
                    status=AccountStatus.ACTIVE,
                )
            )
            await session.commit()
    finally:
        await engine.dispose()
    print(f"SUPER_ADMIN cree : {normalized}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cree un compte SUPER_ADMIN")
    parser.add_argument("--phone", required=True, help="numero de telephone")
    parser.add_argument("--company", required=True, help="nom de l'operateur")
    args = parser.parse_args()

    password = getpass.getpass("Mot de passe SUPER_ADMIN : ")
    if len(password) < 10:
        raise SystemExit("Mot de passe trop court (10 caracteres minimum)")

    asyncio.run(_create(args.phone, args.company, password))


if __name__ == "__main__":
    main()
