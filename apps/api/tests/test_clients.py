from pathlib import Path

import httpx

from pressradar.config import Settings
from pressradar.main import create_app


def create_test_client(database_path: Path) -> httpx.AsyncClient:
    app = create_app(Settings(database_path=str(database_path)))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def sign_up(client: httpx.AsyncClient, email: str) -> None:
    response = await client.post(
        "/auth/signup",
        json={"email": email, "name": "Owner", "password": "secure-passphrase"},
    )
    assert response.status_code == 201


def client_payload() -> dict[str, object]:
    return {
        "name": "Dr. Amina Noor",
        "company": "Nexa AI",
        "website": "https://nexa.example.com",
        "industry": "Artificial intelligence",
        "description": "AI infrastructure for regulated industries.",
        "location": "Dubai, UAE",
        "expertise": ["AI governance", "Fintech"],
        "spokesperson_name": "Amina Noor",
        "spokesperson_title": "Founder",
        "keywords": ["Nexa AI", "AI regulation"],
        "excluded_keywords": ["consumer gadgets"],
        "preferred_topics": ["Responsible AI"],
        "tone": "Authoritative and practical",
        "monitoring_rules": ["Dubai AI startup", "UAE AI regulation"],
    }


async def test_create_list_and_view_client_with_monitoring_rules(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "clients.db") as client:
        await sign_up(client, "owner@example.com")
        created = await client.post("/clients", json=client_payload())
        listed = await client.get("/clients")
        viewed = await client.get(f"/clients/{created.json()['id']}")

    assert created.status_code == 201
    assert created.json()["monitoring_rules"] == ["Dubai AI startup", "UAE AI regulation"]
    assert listed.status_code == 200
    assert listed.json() == [created.json()]
    assert viewed.json() == created.json()


async def test_update_client_replaces_profile_and_monitoring_rules(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "clients.db") as client:
        await sign_up(client, "owner@example.com")
        created = await client.post("/clients", json=client_payload())
        payload = client_payload() | {
            "company": "Nexa Labs",
            "monitoring_rules": ["digital banking UAE"],
        }
        updated = await client.put(f"/clients/{created.json()['id']}", json=payload)

    assert updated.status_code == 200
    assert updated.json()["company"] == "Nexa Labs"
    assert updated.json()["monitoring_rules"] == ["digital banking UAE"]


async def test_client_access_is_isolated_by_workspace(tmp_path: Path) -> None:
    database = tmp_path / "clients.db"
    async with create_test_client(database) as owner:
        await sign_up(owner, "owner@example.com")
        created = await owner.post("/clients", json=client_payload())
    async with create_test_client(database) as outsider:
        await sign_up(outsider, "outsider@example.com")
        listed = await outsider.get("/clients")
        viewed = await outsider.get(f"/clients/{created.json()['id']}")
        updated = await outsider.put(f"/clients/{created.json()['id']}", json=client_payload())

    assert listed.json() == []
    assert viewed.status_code == 404
    assert updated.status_code == 404


async def test_client_routes_require_authentication(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "clients.db") as client:
        response = await client.get("/clients")

    assert response.status_code == 401


async def test_client_input_rejects_invalid_urls_and_blank_rules(tmp_path: Path) -> None:
    payload = client_payload() | {
        "website": "javascript:alert(1)",
        "monitoring_rules": ["   "],
    }
    async with create_test_client(tmp_path / "clients.db") as client:
        await sign_up(client, "owner@example.com")
        response = await client.post("/clients", json=payload)

    assert response.status_code == 422


async def test_client_updates_are_allowed_from_the_configured_web_origin(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "clients.db") as client:
        response = await client.options(
            "/clients/client-id",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "PUT",
            },
        )

    assert response.status_code == 200
    assert "PUT" in response.headers["access-control-allow-methods"]
