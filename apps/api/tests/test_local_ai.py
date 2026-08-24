from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx

from pressradar.config import Settings
from pressradar.infrastructure.ollama_runtime import OllamaRuntime
from pressradar.main import create_app


def runtime_with_mock_provider() -> tuple[OllamaRuntime, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": []})
        if request.url.path == "/api/show":
            return httpx.Response(404)
        if request.url.path == "/api/pull":
            return httpx.Response(200, json={"status": "success"})
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


async def test_local_ai_can_be_deactivated_and_reactivated(tmp_path: Path) -> None:
    runtime, _ = runtime_with_mock_provider()
    async with authenticated_client(tmp_path / "toggle-ai.db", runtime) as client:
        deactivated = await client.delete("/local-ai/active")
        activated = await client.post("/local-ai/active")

    assert deactivated.json()["enabled"] is False
    assert activated.json()["enabled"] is True
    assert activated.json()["model_available"] is False


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
