import asyncio
from pathlib import Path

import httpx

from pressradar.config import Settings
from pressradar.main import create_app


def test_health_reports_ready_local_api(tmp_path: Path) -> None:
    app = create_app(Settings(database_path=str(tmp_path / "health.db")))

    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "local"}
