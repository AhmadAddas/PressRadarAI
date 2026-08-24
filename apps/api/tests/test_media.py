from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from pressradar.application.media import InvalidMediaItemError, MediaIngestionService
from pressradar.config import Settings
from pressradar.domain.media import IncomingMediaItem, MediaSourceType
from pressradar.infrastructure.simulated_media import SimulatedMediaProvider
from pressradar.infrastructure.sqlite_media import SQLiteMediaRepository
from pressradar.main import create_app


def create_test_client(database_path: Path) -> httpx.AsyncClient:
    app = create_app(Settings(database_path=str(database_path)))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def sign_up(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/auth/signup",
        json={
            "email": "media-owner@example.com",
            "name": "Media Owner",
            "password": "secure-passphrase",
        },
    )
    assert response.status_code == 201
    switched = await client.post("/auth/workspace", json={"workspace_kind": "demo"})
    assert switched.status_code == 200


async def test_simulated_ingestion_is_deterministic_and_deduplicated(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "media.db") as client:
        await sign_up(client)
        first = await client.post("/media/ingest")
        second = await client.post("/media/ingest")
        media = await client.get("/media")

    assert first.json() == {"created": 3, "restored": 0, "duplicates": 0}
    assert second.json() == {"created": 0, "restored": 0, "duplicates": 3}
    assert len(media.json()) == 3
    urgent = next(item for item in media.json() if item["source_type"] == "journalist_request")
    assert urgent["deadline"] is not None
    assert "AI governance" in urgent["topics"]


async def test_deleted_media_is_restored_by_the_next_ingestion(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "restore-media.db") as client:
        await sign_up(client)
        await client.post("/media/ingest")
        original = (await client.get("/media")).json()
        deleted_id = original[0]["id"]
        assert (await client.delete(f"/media/{deleted_id}")).status_code == 204

        result = await client.post("/media/ingest")
        restored = (await client.get("/media")).json()

    assert result.json() == {"created": 0, "restored": 1, "duplicates": 2}
    assert {item["id"] for item in restored} == {item["id"] for item in original}


async def test_media_routes_require_authentication(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "media.db") as client:
        ingest = await client.post("/media/ingest")
        media = await client.get("/media")

    assert ingest.status_code == 401
    assert media.status_code == 401


async def test_media_is_isolated_between_workspaces(tmp_path: Path) -> None:
    database = tmp_path / "isolated-media.db"
    async with create_test_client(database) as first:
        await sign_up(first)
        assert (await first.post("/media/ingest")).json()["created"] == 3

    async with create_test_client(database) as second:
        response = await second.post(
            "/auth/signup",
            json={
                "email": "second-media-owner@example.com",
                "name": "Second Media Owner",
                "password": "secure-passphrase",
            },
        )
        assert response.status_code == 201
        assert (await second.get("/media")).json() == []
        await second.post("/auth/workspace", json={"workspace_kind": "demo"})
        assert (await second.post("/media/ingest")).json()["created"] == 3


async def test_media_list_limit_is_validated(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "media.db") as client:
        await sign_up(client)
        response = await client.get("/media", params={"limit": 101})

    assert response.status_code == 422


def test_provider_items_have_stable_external_ids_with_relative_demo_times() -> None:
    now = datetime(2026, 8, 22, 12, tzinfo=UTC)
    items = SimulatedMediaProvider(lambda: now).fetch_items()

    assert [item.external_id for item in items] == [
        "demo-request-ai-governance-001",
        "demo-news-fintech-001",
        "demo-rss-startups-001",
    ]
    assert items[0].deadline is not None
    assert items[0].deadline > now


def test_normalization_rejects_untrusted_provider_urls(tmp_path: Path) -> None:
    item = IncomingMediaItem(
        source="Unsafe provider",
        source_type=MediaSourceType.NEWS,
        headline="Unsafe URL",
        body="External content",
        url="javascript:alert(1)",
        published_at=datetime.now(UTC),
    )

    class UnsafeProvider:
        def fetch_items(self) -> tuple[IncomingMediaItem, ...]:
            return (item,)

    repository = SQLiteMediaRepository(str(tmp_path / "unsafe.db"))
    repository.initialize()

    with pytest.raises(InvalidMediaItemError):
        MediaIngestionService(UnsafeProvider(), repository).ingest(workspace_id="workspace")
