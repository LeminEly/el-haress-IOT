"""Routes d'administration plateforme — reservees au SUPER_ADMIN."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.auth_models import AccountRole
from ..auth.dependencies import Principal, require_role
from ..db.session import get_session
from .admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])

_super_admin = require_role(AccountRole.SUPER_ADMIN)


@router.get("/overview", summary="Vue d'ensemble plateforme (SUPER_ADMIN)")
async def overview(
    _: Principal = Depends(_super_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"data": await AdminService(session).overview()}
