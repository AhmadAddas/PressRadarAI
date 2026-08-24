from pathlib import Path

import httpx

from pressradar.config import Settings
from pressradar.main import create_app


def create_test_client(database_path: Path) -> httpx.AsyncClient:
    app = create_app(Settings(database_path=str(database_path), ai_provider="fake"))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def sign_up(client: httpx.AsyncClient, email: str = "owner@example.com") -> None:
    response = await client.post(
        "/auth/signup",
        json={"email": email, "name": "Owner", "password": "secure-passphrase"},
    )
    assert response.status_code == 201
    assert (
        await client.post("/auth/workspace", json={"workspace_kind": "demo"})
    ).status_code == 200


async def create_nadia(client: httpx.AsyncClient, *, excluded: list[str] | None = None) -> None:
    response = await client.post(
        "/clients",
        json={
            "name": "Nadia Rahman",
            "company": "VertexAI Labs",
            "industry": "Artificial Intelligence",
            "location": "Dubai",
            "expertise": ["AI governance", "AI startup growth"],
            "keywords": ["UAE technology ecosystem"],
            "excluded_keywords": excluded or [],
            "monitoring_rules": ["Dubai AI startup"],
        },
    )
    assert response.status_code == 201


async def test_ingestion_creates_idempotent_matching_opportunity(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "opportunities.db") as client:
        await sign_up(client)
        await create_nadia(client)
        first = await client.post("/media/ingest")
        second = await client.post("/media/ingest")
        response = await client.get("/opportunities")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(response.json()) == 1
    opportunity = response.json()[0]
    assert opportunity["client_name"] == "Nadia Rahman"
    assert opportunity["headline"] == "Dubai AI founders wanted for governance commentary"
    assert opportunity["matched_topics"] == ["AI governance", "Dubai"]
    assert opportunity["status"] == "ready"
    assert opportunity["relevance_score"] == 91
    assert "Nadia Rahman" in opportunity["relevance_reason"]
    assert opportunity["pitch"] is not None


async def test_excluded_keyword_prevents_opportunity(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "excluded.db") as client:
        await sign_up(client)
        await create_nadia(client, excluded=["early-stage startups"])
        await client.post("/media/ingest")
        response = await client.get("/opportunities")

    assert response.json() == []


async def test_opportunity_state_transitions_are_guarded(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "states.db") as client:
        await sign_up(client)
        await create_nadia(client)
        await client.post("/media/ingest")
        opportunity_id = (await client.get("/opportunities")).json()[0]["id"]
        dismissed = await client.patch(
            f"/opportunities/{opportunity_id}/status", json={"status": "dismissed"}
        )
        invalid = await client.patch(
            f"/opportunities/{opportunity_id}/status", json={"status": "sent"}
        )

    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "dismissed"
    assert invalid.status_code == 409


async def test_approved_opportunity_can_still_be_dismissed(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "approved-dismissal.db") as client:
        await sign_up(client)
        await create_nadia(client)
        await client.post("/media/ingest")
        opportunity_id = (await client.get("/opportunities")).json()[0]["id"]
        approved = await client.post(f"/opportunities/{opportunity_id}/approve")
        dismissed = await client.patch(
            f"/opportunities/{opportunity_id}/status", json={"status": "dismissed"}
        )

    assert approved.status_code == 200
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "dismissed"


async def test_opportunities_are_workspace_isolated(tmp_path: Path) -> None:
    database = tmp_path / "isolated.db"
    async with create_test_client(database) as first:
        await sign_up(first, "first@example.com")
        await create_nadia(first)
        await first.post("/media/ingest")
        opportunity_id = (await first.get("/opportunities")).json()[0]["id"]

    async with create_test_client(database) as second:
        await sign_up(second, "second@example.com")
        listed = await second.get("/opportunities")
        changed = await second.patch(
            f"/opportunities/{opportunity_id}/status", json={"status": "dismissed"}
        )

    assert listed.json() == []
    assert changed.status_code == 404


async def test_opportunity_routes_require_authentication(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "auth.db") as client:
        response = await client.get("/opportunities")

    assert response.status_code == 401
