from pathlib import Path
from typing import cast

import httpx

from pressradar.application.analytics import AnalyticsError, AnalyticsStore
from pressradar.config import Settings
from pressradar.domain.analytics import AnalyticsSummary, ProductEvent
from pressradar.infrastructure.sqlite_connection import connect
from pressradar.main import create_app


def create_test_client(
    database_path: Path,
    analytics_path: Path,
    analytics_store: AnalyticsStore | None = None,
) -> httpx.AsyncClient:
    app = create_app(
        Settings(
            database_path=str(database_path),
            analytics_database_path=str(analytics_path),
            ai_provider="fake",
        ),
        analytics_store=analytics_store,
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def sign_up(client: httpx.AsyncClient, email: str) -> None:
    response = await client.post(
        "/auth/signup",
        json={"email": email, "name": "Owner", "password": "secure-passphrase"},
    )
    assert response.status_code == 201


async def test_product_events_feed_workspace_scoped_summary(tmp_path: Path) -> None:
    operational = tmp_path / "operational.db"
    analytics = tmp_path / "analytics.db"
    async with create_test_client(operational, analytics) as owner:
        await sign_up(owner, "analytics-owner@example.com")
        await owner.post("/auth/workspace", json={"workspace_kind": "demo"})
        assert (await owner.post("/demo/setup")).status_code == 200
        assert (await owner.post("/demo/setup")).status_code == 200
        assert (await owner.post("/media/ingest")).status_code == 200
        opportunities = (await owner.get("/opportunities")).json()
        nadia = next(item for item in opportunities if item["client_name"] == "Nadia Rahman")
        samir = next(item for item in opportunities if item["client_name"] == "Samir Qureshi")
        pitch = cast(dict[str, str], nadia["pitch"])
        await owner.put(
            f"/opportunities/{nadia['id']}/pitch",
            json={"content": pitch["content"] + " Reviewed."},
        )
        await owner.post(f"/opportunities/{nadia['id']}/approve")
        await owner.post(f"/opportunities/{nadia['id']}/send")
        await owner.patch(f"/opportunities/{samir['id']}/status", json={"status": "dismissed"})
        summary = await owner.get("/analytics/summary")

    async with create_test_client(operational, analytics) as other:
        await sign_up(other, "analytics-other@example.com")
        isolated = await other.get("/analytics/summary")

    payload = summary.json()
    assert payload["opportunities_detected"] == 3
    assert payload["average_relevance_score"] == 87.33
    assert payload["average_seconds_to_review"] >= 0
    assert payload["average_seconds_to_send"] >= 0
    assert payload["approval_rate"] == 0.3333
    assert payload["pitch_send_rate"] == 0.3333
    assert payload["dismissal_rate"] == 0.3333
    assert sum(source["opportunities"] for source in payload["sources"]) == 3
    assert len(payload["clients"]) == 3
    assert isolated.json()["opportunities_detected"] == 0
    with connect(str(operational)) as connection:
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name = 'product_events'"
            ).fetchone()
            is None
        )
    with connect(str(analytics)) as connection:
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name = 'opportunities'"
            ).fetchone()
            is None
        )


async def test_analytics_summary_requires_authentication(tmp_path: Path) -> None:
    async with create_test_client(
        tmp_path / "auth-operational.db", tmp_path / "auth-analytics.db"
    ) as client:
        response = await client.get("/analytics/summary")

    assert response.status_code == 401


class FailingAnalyticsStore:
    def record(self, event: ProductEvent) -> None:
        raise AnalyticsError("unavailable")

    def summary(self, *, workspace_id: str) -> AnalyticsSummary:
        raise AnalyticsError("unavailable")


async def test_analytics_failure_does_not_block_opportunity_workflow(tmp_path: Path) -> None:
    async with create_test_client(
        tmp_path / "failure-operational.db",
        tmp_path / "unused-analytics.db",
        FailingAnalyticsStore(),
    ) as client:
        await sign_up(client, "analytics-failure@example.com")
        await client.post("/auth/workspace", json={"workspace_kind": "demo"})
        await client.post(
            "/clients",
            json={
                "name": "Nadia Rahman",
                "company": "VertexAI Labs",
                "location": "Dubai",
                "expertise": ["AI governance"],
            },
        )
        ingestion = await client.post("/media/ingest")
        opportunities = await client.get("/opportunities")
        report = await client.get("/analytics/summary")

    assert ingestion.status_code == 200
    assert opportunities.json()[0]["status"] == "ready"
    assert report.status_code == 503
