"""Fixtures de test partagees.

Garde-fou : la suite TRUNCATE les tables. Pour ne jamais detruire une base
reelle, on refuse de demarrer si la base ciblee ne se nomme pas explicitement
comme une base de test (suffixe `_test`). Surchargez via `DATABASE_URL`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import Settings, get_settings
from src.main import create_app


def _require_test_database() -> None:
    db_url = get_settings().database_url
    db_name = db_url.rsplit("/", 1)[-1].split("?", 1)[0]
    if not db_name.endswith("_test"):
        pytest.exit(
            f"Refus d'executer les tests sur la base '{db_name}' : la suite TRUNCATE "
            "les tables. Pointez DATABASE_URL vers une base suffixee '_test' "
            "(ex. el_haress_test).",
            returncode=2,
        )


_require_test_database()


@pytest.fixture
def settings() -> Settings:
    return Settings(environment="testing", cors_origins="http://localhost:5173")


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))
