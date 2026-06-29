"""Fixtures de test partagees."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(environment="testing", cors_origins="http://localhost:5173")


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))
