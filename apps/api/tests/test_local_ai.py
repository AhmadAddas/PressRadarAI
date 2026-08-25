import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest

from pressradar.config import Settings
from pressradar.infrastructure.ollama_runtime import LocalAIError, OllamaRuntime
from pressradar.main import create_app


def runtime_with_mock_provider() -> tuple[OllamaRuntime, list[httpx.Request]]:
    requests: list[httpx.Request] = []
    installed_models: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={"models": [{"name": model} for model in installed_models]},
            )
        if request.url.path == "/api/show":
            return httpx.Response(404)
        if request.url.path == "/api/pull":
            payload = json.loads(request.content)
            model = payload["model"]
            if model == "broken:latest" and payload.get("stream"):
                return httpx.Response(200, text='{"error":"model not found"}\n')
            if model not in installed_models:
                installed_models.append(model)
            if payload.get("stream"):
                return httpx.Response(
                    200,
                    text=(
                        '{"status":"pulling manifest","completed":50,"total":100}\n'
                        '{"status":"success","completed":100,"total":100}\n'
                    ),
                )
            return httpx.Response(200, json={"status": "success"})
        if request.url.path == "/api/delete":
            model = json.loads(request.content)["model"]
            if model in installed_models:
                installed_models.remove(model)
            return httpx.Response(200, json={"status": "success"})
        if request.url.path == "/api/generate":
            payload = json.loads(request.content)
            assert payload["model"] == "translategemma:4b"
            prompt = str(payload["prompt"])
            assert "into Arabic (locale ar)" in prompt
            assert payload["options"] == {"temperature": 0, "num_predict": 512}
            source_texts = json.loads(prompt.split("INPUT: ", maxsplit=1)[1])
            translations = [f"عربي {index}" for index, _ in enumerate(source_texts)]
            if len(source_texts) > 1 and source_texts[0].startswith("Retry"):
                translations.pop()
            if source_texts == ["Cannot translate"]:
                translations.clear()
            if source_texts == ["Chinese hallucination"]:
                translations = ["工作区"]
            return httpx.Response(
                200,
                json={"response": json.dumps({"translations": translations})},
            )
        if request.url.host == "huggingface.co":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "Qwen/Qwen2.5-0.5B-Instruct",
                        "cardData": {"license": "apache-2.0"},
                    }
                ],
            )
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(respond))
    return (
        OllamaRuntime(
            base_url="http://ollama:11434",
            model="llama3.2:3b",
            timeout_seconds=2,
            enabled=True,
            client=client,
        ),
        requests,
    )


@asynccontextmanager
async def authenticated_client(
    database_path: Path, runtime: OllamaRuntime
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(
        Settings(database_path=str(database_path), ai_provider="ollama"),
        ollama_runtime=runtime,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/auth/signup",
            json={
                "email": "local-ai@example.com",
                "name": "Amina",
                "password": "secure-passphrase",
            },
        )
        yield client


async def test_local_ai_license_is_reviewed_before_model_pull(tmp_path: Path) -> None:
    runtime, requests = runtime_with_mock_provider()
    async with authenticated_client(tmp_path / "local-ai.db", runtime) as client:
        preview = await client.post("/local-ai/license", json={"model": "qwen2.5:0.5b-instruct"})
        pulled = await client.post(
            "/local-ai/models",
            json={
                "model": "qwen2.5:0.5b-instruct",
                "accepted_license": "apache-2.0",
            },
        )

    assert preview.status_code == 200
    assert preview.json()["name"] == "apache-2.0"
    assert "commercial use" in preview.json()["summary"]
    assert pulled.status_code == 200
    assert pulled.json()["model"] == "qwen2.5:0.5b-instruct"
    assert any(request.url.path == "/api/pull" for request in requests)


async def test_local_ai_model_can_be_pulled_without_activation(tmp_path: Path) -> None:
    runtime, requests = runtime_with_mock_provider()
    async with authenticated_client(tmp_path / "clone-only.db", runtime) as client:
        await client.delete("/local-ai/active")
        pulled = await client.post(
            "/local-ai/models",
            json={
                "model": "qwen2.5:0.5b-instruct",
                "accepted_license": "apache-2.0",
                "activate": False,
            },
        )

    assert pulled.status_code == 200
    assert pulled.json()["enabled"] is False
    assert pulled.json()["model"] == "llama3.2:3b"
    assert any(request.url.path == "/api/pull" for request in requests)


async def test_local_ai_can_be_deactivated_and_reactivated(tmp_path: Path) -> None:
    runtime, _ = runtime_with_mock_provider()
    async with authenticated_client(tmp_path / "toggle-ai.db", runtime) as client:
        deactivated = await client.delete("/local-ai/active")
        activated = await client.post("/local-ai/active")

    assert deactivated.json()["enabled"] is False
    assert activated.status_code == 409
    assert "before activating" in activated.json()["detail"]


async def test_local_ai_streams_model_pull_progress(tmp_path: Path) -> None:
    runtime, _ = runtime_with_mock_provider()
    async with authenticated_client(tmp_path / "stream-pull.db", runtime) as client:
        response = await client.post(
            "/local-ai/models/stream",
            json={
                "model": "qwen2.5:0.5b-instruct",
                "accepted_license": "apache-2.0",
                "activate": False,
            },
        )

    assert response.status_code == 200
    events = [event for event in response.text.splitlines() if event]
    assert any('"completed": 50' in event and '"total": 100' in event for event in events)
    assert any('"status": "success"' in event for event in events)
    assert '"done": true' in events[-1]


def test_failed_model_pull_does_not_activate_local_ai() -> None:
    runtime, _ = runtime_with_mock_provider()
    runtime.deactivate()

    events = list(runtime.pull_model_events("broken:latest", activate=True))

    assert events == [{"error": "model not found"}]
    assert runtime.status().enabled is False


async def test_installed_model_can_be_activated_and_deleted(tmp_path: Path) -> None:
    runtime, requests = runtime_with_mock_provider()
    async with authenticated_client(tmp_path / "manage-model.db", runtime) as client:
        await client.post(
            "/local-ai/models",
            json={
                "model": "qwen2.5:0.5b-instruct",
                "accepted_license": "apache-2.0",
                "activate": False,
            },
        )
        activated = await client.post(
            "/local-ai/models/active",
            json={"model": "qwen2.5:0.5b-instruct"},
        )
        deleted = await client.delete("/local-ai/models", params={"model": "qwen2.5:0.5b-instruct"})

    assert activated.status_code == 200
    assert activated.json()["enabled"] is True
    assert activated.json()["model"] == "qwen2.5:0.5b-instruct"
    assert deleted.status_code == 200
    assert deleted.json()["enabled"] is False
    assert deleted.json()["installed_models"] == []
    assert any(request.url.path == "/api/delete" for request in requests)


async def test_local_ai_rejects_unknown_or_changed_license_confirmation(
    tmp_path: Path,
) -> None:
    runtime, requests = runtime_with_mock_provider()
    async with authenticated_client(tmp_path / "license-change.db", runtime) as client:
        response = await client.post(
            "/local-ai/models",
            json={"model": "qwen2.5:0.5b-instruct", "accepted_license": "MIT"},
        )

    assert response.status_code == 502
    assert not any(request.url.path == "/api/pull" for request in requests)


async def test_local_ai_translates_an_ordered_text_batch(tmp_path: Path) -> None:
    runtime, _ = runtime_with_mock_provider()
    async with authenticated_client(tmp_path / "translation.db", runtime) as client:
        response = await client.post(
            "/local-ai/translate",
            json={
                "language_code": "ar",
                "language_name": "Arabic",
                "texts": ["Opportunity dashboard", "Add client"],
            },
        )

    assert response.status_code == 200
    assert response.json()["translations"] == ["عربي 0", "عربي 1"]


async def test_local_ai_splits_large_translation_requests_for_small_models(
    tmp_path: Path,
) -> None:
    runtime, requests = runtime_with_mock_provider()
    texts = [f"Dashboard text {index}" for index in range(17)]
    async with authenticated_client(tmp_path / "translation-batches.db", runtime) as client:
        response = await client.post(
            "/local-ai/translate",
            json={
                "language_code": "ar",
                "language_name": "Arabic",
                "texts": texts,
            },
        )

    assert response.status_code == 200
    assert len(response.json()["translations"]) == len(texts)
    generate_requests = [request for request in requests if request.url.path == "/api/generate"]
    assert len(generate_requests) == 3


async def test_local_ai_preserves_an_individually_untranslatable_string(
    tmp_path: Path,
) -> None:
    runtime, _ = runtime_with_mock_provider()
    async with authenticated_client(tmp_path / "translation-fallback.db", runtime) as client:
        response = await client.post(
            "/local-ai/translate",
            json={
                "language_code": "ar",
                "language_name": "Arabic",
                "texts": ["Cannot translate"],
            },
        )

    assert response.status_code == 200
    assert response.json()["translations"] == ["Cannot translate"]


async def test_local_ai_rejects_wrong_script_for_arabic_translation(
    tmp_path: Path,
) -> None:
    runtime, _ = runtime_with_mock_provider()
    async with authenticated_client(tmp_path / "translation-script.db", runtime) as client:
        response = await client.post(
            "/local-ai/translate",
            json={
                "language_code": "ar",
                "language_name": "Arabic",
                "texts": ["Chinese hallucination"],
            },
        )

    assert response.status_code == 200
    assert response.json()["translations"] == ["Chinese hallucination"]


async def test_local_ai_retries_incomplete_batches_as_smaller_requests(
    tmp_path: Path,
) -> None:
    runtime, requests = runtime_with_mock_provider()
    async with authenticated_client(tmp_path / "translation-retry.db", runtime) as client:
        response = await client.post(
            "/local-ai/translate",
            json={
                "language_code": "ar",
                "language_name": "Arabic",
                "texts": ["Retry first", "Retry second"],
            },
        )

    assert response.status_code == 200
    assert response.json()["translations"] == ["عربي 0", "عربي 0"]
    generate_requests = [request for request in requests if request.url.path == "/api/generate"]
    assert len(generate_requests) == 3


async def test_public_pages_can_read_status_and_translate_without_a_session(
    tmp_path: Path,
) -> None:
    runtime, _ = runtime_with_mock_provider()
    app = create_app(
        Settings(database_path=str(tmp_path / "public-local-ai.db"), ai_provider="ollama"),
        ollama_runtime=runtime,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        status = await client.get("/local-ai/public-status")
        translation = await client.post(
            "/local-ai/translate",
            json={
                "language_code": "ar",
                "language_name": "Arabic",
                "texts": ["Sign in"],
            },
        )

    assert status.status_code == 200
    assert status.json()["active"] is False
    assert status.json()["translation_model"] == "translategemma:4b"
    assert translation.status_code == 200
    assert translation.json()["translations"] == ["عربي 0"]


def test_required_analysis_and_translation_models_cannot_be_deleted() -> None:
    runtime, _ = runtime_with_mock_provider()

    with pytest.raises(LocalAIError, match="Required Local AI models"):
        runtime.delete_model("llama3.2:3b")
    with pytest.raises(LocalAIError, match="Required Local AI models"):
        runtime.delete_model("translategemma:4b")
