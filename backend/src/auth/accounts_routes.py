"""Routes de gestion des comptes entreprises (SUPER_ADMIN uniquement)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..db.session import get_session
from .accounts_schemas import AccountCreate, AccountRead, AccountUpdate
from .accounts_service import AccountsService
from .auth_models import AccountRole
from .dependencies import Principal, require_role

router = APIRouter(prefix="/accounts", tags=["accounts"])

_super_admin = require_role(AccountRole.SUPER_ADMIN)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    principal: Principal = Depends(_super_admin),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    account = await AccountsService(session, settings).create(
        payload, actor_id=principal.account_id
    )
    return {"data": AccountRead.model_validate(account)}


@router.get("")
async def list_accounts(
    _: Principal = Depends(_super_admin),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    accounts = await AccountsService(session, settings).list_all()
    return {"data": [AccountRead.model_validate(account) for account in accounts]}


@router.patch("/{account_id}")
async def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    principal: Principal = Depends(_super_admin),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    svc = AccountsService(session, settings)
    account = await svc.update(
        account_id,
        actor_id=principal.account_id,
        company_name=payload.company_name,
        contact_email=payload.contact_email,
        language=payload.language,
    )
    if payload.status is not None:
        account = await svc.set_status(account_id, payload.status, actor_id=principal.account_id)
    return {"data": AccountRead.model_validate(account)}
