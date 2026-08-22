import sqlite3
from pathlib import Path
from typing import Any

import httpx
import pytest

from pressradar.application.relevance import RelevanceAnalysisError
from pressradar.config import Settings
from pressradar.domain.clients import Client
from pressradar.domain.media import MediaItem, MediaSourceType
from pressradar.domain.relevance import RelevanceAnalysis
from pressradar.infrastructure.ollama_relevance import OllamaRelevanceAnalyzer
from pressradar.infrastructure.sqlite_opportunities import SQLiteOpportunityRepository
from pressradar.main import create_app


class FailingRelevanceAnalyzer:
    def analyze(self, **_kwargs: object) -> Any:
        raise RelevanceAnalysisError("provider credentials leaked here")


class UngroundedRelevanceAnalyzer:
    def analyze(self, **_kwargs: object) -> RelevanceAnalysis:
        return RelevanceAnalysis(
            score=99,
            reason="Invented client credentials make this relevant.",
            matched_topics=("Fortune 500 customers",),
        )


async def test_provider_failure_marks_opportunity_failed_without_failing_ingestion(
    tmp_path: Path,
) -> None:
    app = create_app(
        Settings(database_path=str(tmp_path / "failed.db"), ai_provider="fake"),
        relevance_analyzer=FailingRelevanceAnalyzer(),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/auth/signup",
            json={
                "email": "failure@example.com",
                "name": "Owner",
                "password": "secure-passphrase",
            },
        )
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
        opportunity = (await client.get("/opportunities")).json()[0]

    assert ingestion.status_code == 200
    assert opportunity["status"] == "failed"
    assert opportunity["relevance_score"] is None
    assert opportunity["analysis_error"] == "Relevance analysis is temporarily unavailable."
    assert "credentials" not in opportunity["analysis_error"]


async def test_ungrounded_provider_topics_are_rejected(tmp_path: Path) -> None:
    app = create_app(
        Settings(database_path=str(tmp_path / "ungrounded.db"), ai_provider="fake"),
        relevance_analyzer=UngroundedRelevanceAnalyzer(),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/auth/signup",
            json={
                "email": "ungrounded@example.com",
                "name": "Owner",
                "password": "secure-passphrase",
            },
        )
        await client.post(
            "/clients",
            json={
                "name": "Nadia Rahman",
                "company": "VertexAI Labs",
                "location": "Dubai",
                "expertise": ["AI governance"],
            },
        )
        await client.post("/media/ingest")
        opportunity = (await client.get("/opportunities")).json()[0]

    assert opportunity["status"] == "failed"
    assert opportunity["relevance_reason"] is None
    assert opportunity["matched_topics"] == ["AI governance", "Dubai"]


def test_ollama_analyzer_validates_structured_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request: dict[str, object] = {}

    def post(url: str, **kwargs: object) -> httpx.Response:
        request.update(url=url, **kwargs)
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "response": (
                    '{"score":94,"reason":"The request matches the known Dubai AI '
                    'governance expertise.","matched_topics":["AI governance","Dubai"]}'
                )
            },
        )

    monkeypatch.setattr(httpx, "post", post)
    result = OllamaRelevanceAnalyzer(
        base_url="http://ollama:11434", model="test-model", timeout_seconds=4
    ).analyze(client=_client(), media_item=_media_item(), matched_topics=("AI governance", "Dubai"))

    assert result.score == 94
    assert result.matched_topics == ("AI governance", "Dubai")
    assert request["url"] == "http://ollama:11434/api/generate"
    assert request["timeout"] == 4
    payload = request["json"]
    assert isinstance(payload, dict)
    assert payload["model"] == "test-model"
    assert "KNOWN CLIENT FACTS" in str(payload["prompt"])
    assert "MEDIA OPPORTUNITY" in str(payload["prompt"])


def test_ollama_analyzer_rejects_invalid_provider_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def post(url: str, **_kwargs: object) -> httpx.Response:
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"response": '{"score":101,"reason":"Invalid","matched_topics":[]}'},
        )

    monkeypatch.setattr(httpx, "post", post)
    analyzer = OllamaRelevanceAnalyzer(
        base_url="http://ollama:11434", model="test-model", timeout_seconds=4
    )

    with pytest.raises(RelevanceAnalysisError):
        analyzer.analyze(
            client=_client(),
            media_item=_media_item(),
            matched_topics=("AI governance",),
        )


def test_existing_opportunity_table_receives_additive_relevance_columns(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE opportunities (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                client_id TEXT NOT NULL,
                media_item_id TEXT NOT NULL,
                matched_topics TEXT NOT NULL,
                status TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                UNIQUE(client_id, media_item_id)
            );
            """
        )

    SQLiteOpportunityRepository(str(database)).initialize()

    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(opportunities)")}
    assert {"relevance_score", "relevance_reason", "analysis_error"} <= columns


def _client() -> Client:
    return Client(
        id="client-1",
        workspace_id="workspace-1",
        name="Nadia Rahman",
        company="VertexAI Labs",
        website=None,
        industry="Artificial Intelligence",
        description=None,
        location="Dubai",
        expertise=("AI governance",),
        spokesperson_name=None,
        spokesperson_title=None,
        keywords=(),
        excluded_keywords=(),
        preferred_topics=(),
        tone=None,
        monitoring_rules=("Dubai AI startup",),
    )


def _media_item() -> MediaItem:
    from datetime import UTC, datetime

    now = datetime(2026, 8, 22, 12, tzinfo=UTC)
    return MediaItem(
        id="media-1",
        source="Gulf Business Desk",
        source_type=MediaSourceType.JOURNALIST_REQUEST,
        headline="Dubai AI founders wanted",
        body="Comment requested on AI governance.",
        published_at=now,
        ingested_at=now,
        author=None,
        journalist="Layla Hassan",
        url=None,
        deadline=now,
        topics=("AI governance", "Dubai"),
        external_id="request-1",
    )
