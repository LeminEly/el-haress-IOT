"""Tests de l'endpoint de sante et du contrat de reponse de base."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert body["data"]["service"] == "el-haress-backend"


def test_health_sets_request_id_header(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.headers.get("X-Request-ID")


def test_unknown_route_returns_problem_details(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    # Contrat d'erreur RFC 7807.
    assert body["status"] == 404
    assert "title" in body
    assert "request_id" in body
