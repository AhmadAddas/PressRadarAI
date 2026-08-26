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


async def test_media_deadline_can_be_set_adjusted_and_cleared(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "media-deadline.db") as client:
        await sign_up(client)
        await client.post("/media/ingest")
        media = (await client.get("/media")).json()
        item = next(record for record in media if record["deadline"] is None)

        added = await client.patch(
            f"/media/{item['id']}/deadline",
            json={"deadline": "2026-08-27T14:30:00+04:00"},
        )
        adjusted = await client.patch(
            f"/media/{item['id']}/deadline",
            json={"deadline": "2026-08-27T16:00:00+04:00"},
        )
        cleared = await client.patch(f"/media/{item['id']}/deadline", json={"deadline": None})

    assert added.status_code == 200
    assert added.json()["deadline"] == "2026-08-27T10:30:00Z"
    assert adjusted.json()["deadline"] == "2026-08-27T12:00:00Z"
    assert cleared.json()["deadline"] is None


async def test_media_deadline_update_is_validated_and_workspace_scoped(tmp_path: Path) -> None:
    database = tmp_path / "media-deadline-scope.db"
    async with create_test_client(database) as owner:
        await sign_up(owner)
        await owner.post("/media/ingest")
        item_id = (await owner.get("/media")).json()[0]["id"]
        naive = await owner.patch(
            f"/media/{item_id}/deadline",
            json={"deadline": "2026-08-27T14:30:00"},
        )

    async with create_test_client(database) as other:
        response = await other.post(
            "/auth/signup",
            json={
                "email": "deadline-other@example.com",
                "name": "Other User",
                "password": "secure-passphrase",
            },
        )
        assert response.status_code == 201
        cross_workspace = await other.patch(f"/media/{item_id}/deadline", json={"deadline": None})

    assert naive.status_code == 422
    assert naive.json() == {"detail": "Media timestamps must include a timezone"}
    assert cross_workspace.status_code == 404


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


def test_ingestion_preserves_long_headline_and_stores_nine_word_ai_summary(
    tmp_path: Path,
) -> None:
    original = (
        "Emirates Engineering launches new materials studio to inspire future aviation "
        "leaders across the United Arab Emirates"
    )

    class LongHeadlineProvider:
        def fetch_items(self) -> tuple[IncomingMediaItem, ...]:
            return (
                IncomingMediaItem(
                    source="Emirates Media Centre",
                    source_type=MediaSourceType.NEWS,
                    headline=original,
                    body="A new aviation materials studio has opened.",
                    published_at=datetime.now(UTC),
                ),
            )

    class RecordingSummarizer:
        def __init__(self) -> None:
            self.requests: list[tuple[str, int]] = []

        def summarize_headline(self, headline: str, *, max_words: int) -> str:
            self.requests.append((headline, max_words))
            return "Emirates Engineering opens materials studio for future aviation leaders"

    repository = SQLiteMediaRepository(str(tmp_path / "headlines.db"))
    repository.initialize()
    summarizer = RecordingSummarizer()

    MediaIngestionService(LongHeadlineProvider(), repository, summarizer).ingest(
        workspace_id="workspace"
    )
    stored = repository.list(workspace_id="workspace", limit=10)[0]

    assert summarizer.requests == [(original, 9)]
    assert stored.headline == original
    assert stored.display_headline == (
        "Emirates Engineering opens materials studio for future aviation leaders"
    )
    assert len(stored.display_headline.split()) <= 9


def test_ingestion_does_not_summarize_thirteen_word_headline(tmp_path: Path) -> None:
    headline = "one two three four five six seven eight nine ten eleven twelve thirteen"

    class BoundaryProvider:
        def fetch_items(self) -> tuple[IncomingMediaItem, ...]:
            return (
                IncomingMediaItem(
                    source="Boundary",
                    source_type=MediaSourceType.NEWS,
                    headline=headline,
                    body="Boundary body",
                    published_at=datetime.now(UTC),
                ),
            )

    class UnexpectedSummarizer:
        def summarize_headline(self, headline: str, *, max_words: int) -> str:
            raise AssertionError("Thirteen-word headlines must not be summarized")

    repository = SQLiteMediaRepository(str(tmp_path / "headline-boundary.db"))
    repository.initialize()
    MediaIngestionService(BoundaryProvider(), repository, UnexpectedSummarizer()).ingest(
        workspace_id="workspace"
    )

    stored = repository.list(workspace_id="workspace", limit=10)[0]
    assert stored.headline == headline
    assert stored.display_headline is None
