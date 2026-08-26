import socket
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from pressradar.config import Settings
from pressradar.main import create_app


def create_test_client(database_path: Path) -> httpx.AsyncClient:
    app = create_app(Settings(database_path=str(database_path)))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def sign_up(client: httpx.AsyncClient, email: str = "sources@example.com") -> None:
    response = await client.post(
        "/auth/signup",
        json={"email": email, "name": "Source Owner", "password": "secure-passphrase"},
    )
    assert response.status_code == 201


async def test_prod_sources_can_be_created_filtered_and_deleted(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "sources.db") as client:
        await sign_up(client)
        rss = await client.post(
            "/media/sources",
            json={
                "name": "UAE business feed",
                "kind": "rss",
                "url": "https://example.com/business.xml",
            },
        )
        api = await client.post(
            "/media/sources",
            json={"name": "UAE NewsAPI", "kind": "api", "provider": "newsapi"},
        )
        filtered = await client.get("/media/sources", params={"kind": "rss"})
        deleted = await client.delete(f"/media/sources/{rss.json()['id']}")
        remaining = await client.get("/media/sources")

    assert rss.status_code == 201
    assert api.status_code == 201
    assert [source["kind"] for source in filtered.json()] == ["rss"]
    assert deleted.status_code == 204
    assert [source["provider"] for source in remaining.json()] == ["newsapi"]


async def test_source_configuration_is_workspace_scoped_and_prod_only(tmp_path: Path) -> None:
    database = tmp_path / "isolated-sources.db"
    async with create_test_client(database) as owner:
        await sign_up(owner)
        created = await owner.post(
            "/media/sources",
            json={"name": "NewsAPI", "kind": "api", "provider": "newsapi"},
        )
        await owner.post("/auth/workspace", json={"workspace_kind": "demo"})
        demo_list = await owner.get("/media/sources")

    async with create_test_client(database) as other:
        await sign_up(other, "other-sources@example.com")
        other_list = await other.get("/media/sources")
        cross_delete = await other.delete(f"/media/sources/{created.json()['id']}")

    assert demo_list.status_code == 409
    assert other_list.json() == []
    assert cross_delete.status_code == 404


async def test_source_validation_and_uae_suggestions(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "suggestions.db") as client:
        await sign_up(client)
        insecure = await client.post(
            "/media/sources",
            json={"name": "Unsafe", "kind": "rss", "url": "http://localhost/feed"},
        )
        suggestions = await client.get("/media/sources/suggestions", params={"kind": "api"})
        configured = await client.post(
            "/media/sources",
            json={"name": "My NewsAPI", "kind": "api", "provider": "newsapi"},
        )
        suggestions_after_add = await client.get(
            "/media/sources/suggestions", params={"kind": "api"}
        )
        await client.delete(f"/media/sources/{configured.json()['id']}")
        suggestions_after_delete = await client.get(
            "/media/sources/suggestions", params={"kind": "api"}
        )

    assert insecure.status_code == 422
    assert suggestions.json() == [
        {
            "name": "UAE headlines via NewsAPI",
            "kind": "api",
            "provider": "newsapi",
            "url": None,
        }
    ]
    assert suggestions_after_add.json() == []
    assert suggestions_after_delete.json() == suggestions.json()


async def test_prod_ingestion_uses_configured_sources_and_requires_provider_key(
    tmp_path: Path,
) -> None:
    async with create_test_client(tmp_path / "prod-ingestion.db") as client:
        await sign_up(client)
        empty = await client.post("/media/ingest")
        await client.post(
            "/media/sources",
            json={"name": "UAE NewsAPI", "kind": "api", "provider": "newsapi"},
        )
        missing_key = await client.post("/media/ingest")

    assert empty.json() == {"created": 0, "restored": 0, "duplicates": 0}
    assert missing_key.status_code == 409
    assert missing_key.json() == {"detail": "NEWSAPI_API_KEY is required for NewsAPI"}


async def test_newsapi_adapter_ingests_uae_articles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    requests: list[tuple[str, dict[str, object]]] = []

    def newsapi_response(url: str, **kwargs: object) -> httpx.Response:
        requests.append((url, kwargs))
        articles = []
        if url.endswith("/everything"):
            articles = [
                {
                    "source": {"name": "UAE Business"},
                    "author": "Reporter",
                    "title": "UAE technology companies expand",
                    "description": "Companies announced new regional investments.",
                    "url": "https://example.com/uae-tech",
                    "publishedAt": "2026-08-22T10:00:00Z",
                }
            ]
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            json={"status": "ok", "totalResults": len(articles), "articles": articles},
        )

    monkeypatch.setattr(httpx, "get", newsapi_response)
    app = create_app(
        Settings(
            database_path=str(tmp_path / "newsapi.db"),
            newsapi_api_key=SecretStr("test-key"),
        )
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await sign_up(client)
        await client.post(
            "/media/sources",
            json={"name": "UAE NewsAPI", "kind": "api", "provider": "newsapi"},
        )
        ingestion = await client.post("/media/ingest")
        media = await client.get("/media")

    assert ingestion.json() == {"created": 1, "restored": 0, "duplicates": 0}
    assert media.json()[0]["headline"] == "UAE technology companies expand"
    assert [request[0] for request in requests] == [
        "https://newsapi.org/v2/top-headlines",
        "https://newsapi.org/v2/everything",
    ]
    assert requests[0][1]["params"] == {"country": "ae", "pageSize": 25}
    assert requests[1][1]["params"] == {
        "q": '"United Arab Emirates" OR UAE OR Dubai OR "Abu Dhabi"',
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 25,
    }
    assert requests[1][1]["headers"] == {"X-Api-Key": "test-key"}


async def test_rss_adapter_ingests_public_feed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: httpx.Response(
            200,
            request=httpx.Request("GET", "https://example.com/feed.xml"),
            content=b"""<rss><channel><item><title>Dubai startup funding</title>
            <description><![CDATA[<p>A UAE startup raised new funding.</p>]]></description>
            <link>https://example.com/story</link><guid>story-1</guid>
            <pubDate>Sat, 22 Aug 2026 10:00:00 GMT</pubDate>
            <deadline>Sat, 22 Aug 2026 14:00:00 GMT</deadline></item></channel></rss>""",
        ),
    )
    async with create_test_client(tmp_path / "rss.db") as client:
        await sign_up(client)
        await client.post(
            "/media/sources",
            json={
                "name": "UAE RSS",
                "kind": "rss",
                "url": "https://example.com/feed.xml",
            },
        )
        ingestion = await client.post("/media/ingest")
        media = await client.get("/media")

    assert ingestion.json() == {"created": 1, "restored": 0, "duplicates": 0}
    assert media.json()[0]["body"] == "A UAE startup raised new funding."
    assert media.json()[0]["deadline"] == "2026-08-22T14:00:00Z"
    assert media.json()[0]["published_at"] == "2026-08-22T10:00:00Z"


async def test_journalist_request_feed_uses_explicit_namespaced_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: httpx.Response(
            200,
            request=httpx.Request("GET", "https://example.com/requests.xml"),
            content=b"""<rss xmlns:req="https://example.com/request"><channel><item>
            <title>Founder needed for UAE AI interview</title>
            <description>Seeking a Dubai founder for expert commentary.</description>
            <guid>request-1</guid><pubDate>Wed, 26 Aug 2026 08:00:00 GMT</pubDate>
            <req:expires>2026-08-26T16:00:00+04:00</req:expires>
            </item></channel></rss>""",
        ),
    )
    async with create_test_client(tmp_path / "journalist-feed.db") as client:
        await sign_up(client)
        source = await client.post(
            "/media/sources",
            json={
                "name": "Licensed journalist requests",
                "kind": "rss",
                "url": "https://example.com/requests.xml",
                "provider": "journalist_requests",
            },
        )
        ingestion = await client.post("/media/ingest")
        media = await client.get("/media")

    assert source.status_code == 201
    assert ingestion.json() == {"created": 1, "restored": 0, "duplicates": 0}
    assert media.json()[0]["source_type"] == "journalist_request"
    assert media.json()[0]["deadline"] == "2026-08-26T12:00:00Z"


async def test_production_ingestion_caps_each_source_and_the_total_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    requests: list[str] = []

    def rss_response(url: str, **kwargs: object) -> httpx.Response:
        requests.append(url)
        items = "".join(
            f"""<item><title>Story {index}</title><description>UAE story {index}</description>
            <guid>{url}-{index}</guid><pubDate>Sat, 22 Aug 2026 10:00:00 GMT</pubDate></item>"""
            for index in range(30)
        )
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            content=f"<rss><channel>{items}</channel></rss>".encode(),
        )

    monkeypatch.setattr(httpx, "get", rss_response)
    async with create_test_client(tmp_path / "bounded-ingestion.db") as client:
        await sign_up(client)
        for index in range(5):
            created = await client.post(
                "/media/sources",
                json={
                    "name": f"Feed {index}",
                    "kind": "rss",
                    "url": f"https://example.com/feed-{index}.xml",
                },
            )
            assert created.status_code == 201

        ingestion = await client.post("/media/ingest")
        media = await client.get("/media", params={"limit": 100})

    assert ingestion.json() == {"created": 100, "restored": 0, "duplicates": 0}
    assert len(media.json()) == 100
    assert len(requests) == 4
