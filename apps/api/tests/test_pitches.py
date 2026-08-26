import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx
import pytest

from pressradar.application.pitches import (
    PitchGenerationError,
    PitchGenerator,
    validate_generated_pitch,
)
from pressradar.config import Settings
from pressradar.domain.clients import Client
from pressradar.domain.media import MediaItem, MediaSourceType
from pressradar.domain.pitches import GeneratedPitch
from pressradar.infrastructure.ollama_pitch import OllamaPitchGenerator
from pressradar.main import create_app


class FailingPitchGenerator:
    def generate(self, **_kwargs: object) -> Any:
        raise PitchGenerationError("provider secret must not leak")


class GenericPitchGenerator:
    def generate(self, **_kwargs: object) -> GeneratedPitch:
        return GeneratedPitch(
            content=(
                "This is a generic response. It does not reference supplied context. "
                "It should be rejected."
            )
        )


def create_test_client(
    database_path: Path, *, pitch_generator: PitchGenerator | None = None
) -> httpx.AsyncClient:
    app = create_app(
        Settings(database_path=str(database_path), ai_provider="fake"),
        pitch_generator=pitch_generator,
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def prepare_opportunity(client: httpx.AsyncClient) -> dict[str, object]:
    signup = await client.post(
        "/auth/signup",
        json={
            "email": "pitch-owner@example.com",
            "name": "Owner",
            "password": "secure-passphrase",
        },
    )
    assert signup.status_code == 201
    assert (
        await client.post("/auth/workspace", json={"workspace_kind": "demo"})
    ).status_code == 200
    created = await client.post(
        "/clients",
        json={
            "name": "Nadia Rahman",
            "company": "VertexAI Labs",
            "location": "Dubai",
            "expertise": ["AI governance", "AI startup growth"],
            "spokesperson_name": "Nadia Rahman",
            "spokesperson_title": "Founder & CEO",
        },
    )
    assert created.status_code == 201
    ingestion = await client.post("/media/ingest")
    assert ingestion.status_code == 200
    payload = (await client.get("/opportunities")).json()
    assert isinstance(payload, list)
    assert isinstance(payload[0], dict)
    return cast(dict[str, object], payload[0])


async def test_ready_opportunity_contains_grounded_three_sentence_pitch(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "pitch.db") as client:
        opportunity = await prepare_opportunity(client)

    pitch = opportunity["pitch"]
    assert isinstance(pitch, dict)
    assert pitch["opportunity_id"] == opportunity["id"]
    assert pitch["content"].count(".") == 3
    assert "Nadia Rahman" in pitch["content"]
    assert "AI governance" in pitch["content"]
    assert opportunity["pitch_error"] is None


async def test_user_can_edit_pitch_only_while_opportunity_is_ready(tmp_path: Path) -> None:
    async with create_test_client(tmp_path / "edit.db") as client:
        opportunity = await prepare_opportunity(client)
        opportunity_id = opportunity["id"]
        edited = await client.put(
            f"/opportunities/{opportunity_id}/pitch",
            json={"content": "A concise user-edited response grounded in verified client facts."},
        )
        await client.post("/media/ingest")
        replayed = (await client.get("/opportunities")).json()[0]
        dismissed = await client.patch(
            f"/opportunities/{opportunity_id}/status", json={"status": "dismissed"}
        )
        blocked = await client.put(
            f"/opportunities/{opportunity_id}/pitch",
            json={"content": "This edit must not be accepted after dismissal."},
        )

    assert edited.status_code == 200
    assert edited.json()["pitch"]["content"].startswith("A concise user-edited")
    assert replayed["pitch"]["content"] == edited.json()["pitch"]["content"]
    assert dismissed.status_code == 200
    assert blocked.status_code == 409


async def test_failed_generation_is_safe_and_user_can_supply_draft(tmp_path: Path) -> None:
    async with create_test_client(
        tmp_path / "failure.db", pitch_generator=FailingPitchGenerator()
    ) as client:
        opportunity = await prepare_opportunity(client)
        updated = await client.put(
            f"/opportunities/{opportunity['id']}/pitch",
            json={"content": "A manually verified draft from the workspace owner."},
        )

    assert opportunity["status"] == "ready"
    assert opportunity["pitch"] is None
    assert opportunity["pitch_error"] == "Pitch generation is temporarily unavailable."
    assert "secret" not in opportunity["pitch_error"]
    assert updated.status_code == 200
    assert updated.json()["pitch_error"] is None
    assert updated.json()["pitch"]["content"].startswith("A manually verified")


async def test_generic_generated_pitch_is_rejected(tmp_path: Path) -> None:
    async with create_test_client(
        tmp_path / "generic.db", pitch_generator=GenericPitchGenerator()
    ) as client:
        opportunity = await prepare_opportunity(client)

    assert opportunity["pitch"] is None
    assert opportunity["pitch_error"] == "Pitch generation is temporarily unavailable."


async def test_pitch_edit_is_workspace_scoped_and_validated(tmp_path: Path) -> None:
    database = tmp_path / "isolation.db"
    async with create_test_client(database) as owner:
        opportunity = await prepare_opportunity(owner)

    async with create_test_client(database) as other:
        signup = await other.post(
            "/auth/signup",
            json={
                "email": "other@example.com",
                "name": "Other",
                "password": "secure-passphrase",
            },
        )
        assert signup.status_code == 201
        hidden = await other.put(
            f"/opportunities/{opportunity['id']}/pitch",
            json={"content": "Attempted cross-workspace edit."},
        )
        blank = await other.put(
            f"/opportunities/{opportunity['id']}/pitch", json={"content": "   "}
        )

    assert hidden.status_code == 404
    assert blank.status_code == 422


def test_ollama_pitch_generator_uses_separated_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request: dict[str, object] = {}

    def post(url: str, **kwargs: object) -> httpx.Response:
        request["url"] = url
        request.update(kwargs)
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "response": json.dumps(
                    {
                        "sentences": [
                            "Nadia Rahman can address the AI governance request",
                            "Her perspective reflects the supplied client expertise",
                            "She can provide concise context for the journalist",
                        ]
                    }
                )
            },
        )

    monkeypatch.setattr(httpx, "post", post)
    generator = OllamaPitchGenerator(
        base_url="http://ollama:11434", model="test-model", timeout_seconds=4
    )

    pitch = generator.generate(client=_client(), media_item=_media_item())

    assert pitch.content.startswith("Nadia Rahman")
    payload = request["json"]
    assert isinstance(payload, dict)
    assert payload["model"] == "test-model"
    assert "concise PR drafting assistant" in str(payload["system"])
    assert payload["options"] == {"temperature": 0, "num_predict": 192}
    assert "format" in payload
    assert "KNOWN CLIENT FACTS" in str(payload["prompt"])
    assert "MEDIA OPPORTUNITY" in str(payload["prompt"])
    assert "Never invent" in str(payload["prompt"])


def test_ollama_pitch_generator_summarizes_only_long_headlines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[dict[str, object]] = []

    def post(url: str, **kwargs: object) -> httpx.Response:
        payload = cast(dict[str, object], kwargs["json"])
        requests.append(payload)
        prompt = str(payload["prompt"])
        generated = (
            '{"headline":"Emirates Engineering launches studio for future aviation innovators"}'
            if "Faithfully summarize" in prompt
            else json.dumps(
                {
                    "sentences": [
                        "Nadia Rahman can address this request",
                        "Her expertise matches the supplied topic",
                        "She can provide useful context",
                    ]
                }
            )
        )
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"response": generated},
        )

    monkeypatch.setattr(httpx, "post", post)
    media = replace(
        _media_item(),
        headline=(
            "Emirates Engineering launches Material Futures Studio to inspire the next "
            "generation of aviation innovators"
        ),
    )

    pitch = OllamaPitchGenerator(
        base_url="http://ollama:11434", model="test-model", timeout_seconds=4
    ).generate(client=_client(), media_item=media)

    assert pitch.display_headline == (
        "Emirates Engineering launches studio for future aviation innovators"
    )
    assert len(pitch.display_headline.split()) <= 13
    assert len(requests) == 2
    assert requests[0]["options"] == {"temperature": 0, "num_predict": 192}
    assert requests[1]["options"] == {"temperature": 0, "num_predict": 64}
    validated = validate_generated_pitch(pitch, client=_client(), media_item=media)
    assert validated.display_headline == pitch.display_headline


def test_ollama_pitch_survives_headline_summary_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def post(url: str, **kwargs: object) -> httpx.Response:
        payload = cast(dict[str, object], kwargs["json"])
        response = (
            "not valid JSON"
            if "Faithfully summarize" in str(payload["prompt"])
            else json.dumps(
                {
                    "sentences": [
                        "Nadia Rahman can address this request",
                        "Her expertise matches the supplied topic",
                        "She can provide useful context",
                    ]
                }
            )
        )
        return httpx.Response(200, request=httpx.Request("POST", url), json={"response": response})

    monkeypatch.setattr(httpx, "post", post)
    media = replace(
        _media_item(),
        headline="one two three four five six seven eight nine ten eleven twelve thirteen fourteen",
    )

    pitch = OllamaPitchGenerator(
        base_url="http://ollama:11434", model="test-model", timeout_seconds=4
    ).generate(client=_client(), media_item=media)

    assert pitch.content.startswith("Nadia Rahman")
    assert pitch.display_headline is None


def test_ollama_pitch_generator_normalizes_verbose_unattributed_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def post(url: str, **_kwargs: object) -> httpx.Response:
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "response": json.dumps(
                    {
                        "sentences": [
                            "1. The request concerns aviation materials. This extra sentence "
                            "must be removed.",
                            "It gives students practical industry experience",
                            "The initiative connects education and engineering",
                        ]
                    }
                )
            },
        )

    monkeypatch.setattr(httpx, "post", post)
    pitch = OllamaPitchGenerator(
        base_url="http://ollama:11434", model="test-model", timeout_seconds=4
    ).generate(client=_client(), media_item=_media_item())

    assert pitch.content.startswith("Nadia Rahman:")
    assert pitch.content.count(".") == 3
    assert "extra sentence" not in pitch.content


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
        spokesperson_name="Nadia Rahman",
        spokesperson_title="Founder & CEO",
        keywords=(),
        excluded_keywords=(),
        preferred_topics=(),
        tone=None,
        monitoring_rules=("Dubai AI startup",),
    )


def _media_item() -> MediaItem:
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
