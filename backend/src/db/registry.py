"""Point d'import unique des modeles.

Importer ce module peuple `Base.metadata` avec toutes les tables, ce dont
Alembic a besoin pour l'autogeneration et les migrations.
"""

from __future__ import annotations

from ..alerting import alerting_models as alerting_models
from ..auth import auth_models as auth_models
from ..sensors import sensors_models as sensors_models
from . import audit_models as audit_models
