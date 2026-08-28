from pathlib import Path

import httpx

from pressradar.config import Settings
from pressradar.infrastructure.sqlite_connection import connect
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
        empty_media = await client.get("/media")
        empty_opportunities = await client.get("/opportunities")
        ingestion = await client.post("/media/ingest")
        opportunities = await client.get("/opportunities")
        opportunity_by_client = {item["client_name"]: item["id"] for item in opportunities.json()}
        with connect(str(database)) as connection:
            connection.execute(
                "UPDATE opportunities SET relevance_score = 80, detected_at = ? WHERE id = ?",
                ("2026-08-22T10:00:00+00:00", opportunity_by_client["Samir Qureshi"]),
            )
            connection.execute(
                "UPDATE opportunities SET relevance_score = 80, detected_at = ? WHERE id = ?",
                ("2026-08-22T11:00:00+00:00", opportunity_by_client["Mariam Al Noor"]),
            )
        recency_ranked = await client.get("/opportunities")
        samir_opportunity = next(
            item for item in opportunities.json() if item["client_name"] == "Samir Qureshi"
        )
        await client.patch(
            f"/media/{samir_opportunity['media_item_id']}/deadline",
            json={"deadline": "2026-08-27T12:00:00Z"},
        )
        deadline_updated = await client.get("/opportunities")

    assert signup.status_code == 201
    assert switched.status_code == 200
    assert first.json() == {
        "clients_created": 3,
        "media_created": 0,
        "opportunities_created": 0,
    }
    assert second.json() == {
        "clients_created": 0,
        "media_created": 0,
        "opportunities_created": 0,
    }
    assert len(clients.json()) == 3
    assert empty_media.json() == []
    assert empty_opportunities.json() == []
    assert ingestion.json() == {"created": 3, "restored": 0, "duplicates": 0}
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
    updated_samir = next(
        item for item in deadline_updated.json() if item["client_name"] == "Samir Qureshi"
    )
    assert updated_samir["deadline"] == "2026-08-27T12:00:00Z"


async def test_demo_setup_requires_authentication(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "demo-auth.db") as client:
        response = await client.post("/demo/setup")

    assert response.status_code == 401


async def test_independent_deletion_preserves_orphaned_opportunity_history(
    tmp_path: Path,
) -> None:
    async with create_test_client(tmp_path / "deletion.db") as client:
        await client.post(
            "/auth/signup",
            json={
                "email": "delete@example.com",
                "name": "Delete Owner",
                "password": "secure-passphrase",
            },
        )
        await client.post("/auth/workspace", json={"workspace_kind": "demo"})
        await client.post("/demo/setup")
        await client.post("/media/ingest")
        opportunity = (await client.get("/opportunities")).json()[0]

        client_deleted = await client.delete(f"/clients/{opportunity['client_id']}")
        after_client = (await client.get("/opportunities")).json()[0]
        media_deleted = await client.delete(f"/media/{opportunity['media_item_id']}")
        after_media = (await client.get("/opportunities")).json()[0]
        opportunity_deleted = await client.delete(f"/opportunities/{opportunity['id']}")
        remaining = await client.get("/opportunities")

    assert client_deleted.status_code == 204
    assert after_client["client_deleted"] is True
    assert after_client["media_deleted"] is False
    assert after_client["client_name"] == opportunity["client_name"]
    assert media_deleted.status_code == 204
    assert after_media["client_deleted"] is True
    assert after_media["media_deleted"] is True
    assert after_media["headline"] == opportunity["headline"]
    assert opportunity_deleted.status_code == 204
    assert all(item["id"] != opportunity["id"] for item in remaining.json())
