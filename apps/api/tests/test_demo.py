import sqlite3
from pathlib import Path

import httpx

from pressradar.config import Settings
from pressradar.main import create_app


def create_test_client(database_path: Path) -> httpx.AsyncClient:
    app = create_app(Settings(database_path=str(database_path)))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_demo_setup_builds_ranked_workspace_and_is_idempotent(tmp_path: Path) -> None:
    database = tmp_path / "demo.db"
    async with create_test_client(database) as client:
        signup = await client.post(
            "/auth/signup",
            json={
                "email": "demo@example.com",
                "name": "Demo User",
                "password": "secure-passphrase",
            },
        )
        switched = await client.post("/auth/workspace", json={"workspace_kind": "demo"})
        first = await client.post("/demo/setup")
        second = await client.post("/demo/setup")
        clients = await client.get("/clients")
        opportunities = await client.get("/opportunities")
        opportunity_by_client = {item["client_name"]: item["id"] for item in opportunities.json()}
        with sqlite3.connect(database) as connection:
            connection.execute(
                "UPDATE opportunities SET relevance_score = 80, detected_at = ? WHERE id = ?",
                ("2026-08-22T10:00:00+00:00", opportunity_by_client["Samir Qureshi"]),
            )
            connection.execute(
                "UPDATE opportunities SET relevance_score = 80, detected_at = ? WHERE id = ?",
                ("2026-08-22T11:00:00+00:00", opportunity_by_client["Mariam Al Noor"]),
            )
        recency_ranked = await client.get("/opportunities")

    assert signup.status_code == 201
    assert switched.status_code == 200
    assert first.json() == {
        "clients_created": 3,
        "media_created": 3,
        "opportunities_created": 3,
    }
    assert second.json() == {
        "clients_created": 0,
        "media_created": 0,
        "opportunities_created": 0,
    }
    assert len(clients.json()) == 3
    assert [item["client_name"] for item in opportunities.json()] == [
        "Nadia Rahman",
        "Samir Qureshi",
        "Mariam Al Noor",
    ]
    assert [item["relevance_score"] for item in opportunities.json()] == [98, 86, 78]
    assert opportunities.json()[0]["deadline"] is not None
    assert all(item["pitch"] for item in opportunities.json())
    assert [item["client_name"] for item in recency_ranked.json()] == [
        "Nadia Rahman",
        "Mariam Al Noor",
        "Samir Qureshi",
    ]


async def test_demo_setup_requires_authentication(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "demo-auth.db") as client:
        response = await client.post("/demo/setup")

    assert response.status_code == 401
