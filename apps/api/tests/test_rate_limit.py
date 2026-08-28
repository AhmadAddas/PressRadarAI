from pathlib import Path

import httpx
import pytest
from fastapi import HTTPException

from pressradar.config import Settings
from pressradar.infrastructure.ollama_runtime import OllamaRuntime
from pressradar.main import create_app
from pressradar.presentation.rate_limit import InMemoryRateLimiter


def test_rate_limiter_rejects_burst_and_resets_after_window() -> None:
    now = 100.0
    limiter = InMemoryRateLimiter(lambda: now)

    limiter.check("signin:test", limit=2, window_seconds=60)
    limiter.check("signin:test", limit=2, window_seconds=60)
    with pytest.raises(HTTPException) as raised:
        limiter.check("signin:test", limit=2, window_seconds=60)
    assert raised.value.status_code == 429
    assert raised.value.headers is not None
    assert raised.value.headers["Retry-After"] == "61"

    now = 161.0
    limiter.check("signin:test", limit=2, window_seconds=60)


async def test_non_operator_cannot_manage_shared_local_ai(tmp_path: Path) -> None:
    runtime = OllamaRuntime(
        base_url="http://ollama:11434",
        model="qwen2.5:0.5b-instruct",
        translation_model="translategemma:4b",
        timeout_seconds=1,
        enabled=False,
    )
    app = create_app(
        Settings(
            database_path=str(tmp_path / "operator.db"),
            ai_provider="ollama",
            email_provider="fake",
            local_ai_admin_emails="operator@example.com",
        ),
        ollama_runtime=runtime,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/auth/signup",
            json={
                "email": "member@example.com",
                "name": "Member",
                "password": "secure-passphrase",
            },
        )
        response = await client.delete("/local-ai/active")

    assert response.status_code == 403
    assert response.json()["detail"] == "Local AI administration requires operator access"


async def test_public_translation_is_rate_limited(tmp_path: Path) -> None:
    runtime = OllamaRuntime(
        base_url="http://ollama:11434",
        model="qwen2.5:0.5b-instruct",
        translation_model="translategemma:4b",
        timeout_seconds=1,
        enabled=False,
    )
    app = create_app(
        Settings(
            database_path=str(tmp_path / "translation-limit.db"),
            ai_provider="ollama",
            translation_rate_limit_requests=1,
        ),
        ollama_runtime=runtime,
    )
    payload = {"language_code": "ar", "language_name": "Arabic", "texts": ["Sign in"]}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/local-ai/translate", json=payload)
        response = await client.post("/local-ai/translate", json=payload)

    assert response.status_code == 429
    assert response.headers["Retry-After"]
