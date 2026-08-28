"""Contexte de tenance et dependance d'isolation.

`TenantContext` porte l'`account_id` et le role issus du jeton authentifie. Toute
la couche service filtre par `context.account_id`. Cet identifiant ne provient
JAMAIS d'un parametre de requete fourni par le client : uniquement du jeton.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends

from ..auth.auth_models import AccountRole
from ..auth.dependencies import Principal, get_current_account


@dataclass(frozen=True)
class TenantContext:
    account_id: uuid.UUID
    role: AccountRole


async def get_tenant_context(
    principal: Principal = Depends(get_current_account),
) -> TenantContext:
    return TenantContext(account_id=principal.account_id, role=principal.role)
